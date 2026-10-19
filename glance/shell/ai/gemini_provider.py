"""
Google Gemini provider — uses the REST SSE streaming API directly (no extra deps).
The model is chosen at runtime from what the key can actually use (see
ai/gemini_models.py), because Google retires model names often.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncIterator, List

import httpx

from ai.base_provider import BaseLLMProvider, Message
from ai.gemini_models import pick_models
from config import cfg

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Process-wide: models that returned 404/403 for this key are not retried, and the
# live model list is refreshed at most every 6 hours.
_bad: set = set()
_cache = {"t": 0.0, "models": []}


class GeminiError(RuntimeError):
    """A Gemini failure with a message that never contains the API key."""


def _hdr(key: str) -> dict:
    return {"x-goog-api-key": key or "", "Content-Type": "application/json"}


def _err_text(resp_text: str, key: str) -> str:
    try:
        msg = json.loads(resp_text)["error"]["message"]
    except Exception:
        msg = resp_text
    return " ".join(str(msg).replace(key or "\0", "***").split())[:240]


# Per-model health: free-tier keys are rate limited PER MODEL (429) and new models
# are often overloaded (503). A failed model sits out for a short cooldown, and the
# model that last worked is tried first, so a turn doesn't re-pay for known failures.
_cool: dict = {}
_nothink: set = set()        # models that reject thinkingConfig
_sticky = {"text": None, "vision": None}


# Speed memory, kept across runs: new Gemini models are often overloaded (503) or slow
# (5+ s), and trying them first on every request cost 10-60 s per turn. We remember
# how fast each model answered (time to first token) and which ones recently failed,
# and try the fastest healthy model first.
_HEALTH_FILE = Path(os.path.expanduser("~/.glance")) / "gemini_health.json"
_lat: dict = {}              # "model|v" or "model|t" -> smoothed seconds to first token
_bad_until: dict = {}        # model -> wall-clock time before which we skip it


def _load_health() -> None:
    try:
        d = json.loads(_HEALTH_FILE.read_text(encoding="utf-8"))
        _lat.update({k: float(v) for k, v in d.get("lat", {}).items()})
        now = time.time()
        _bad_until.update({k: float(v) for k, v in d.get("bad", {}).items() if float(v) > now})
        _nothink.update(d.get("nothink", []))
        _bad.update(d.get("retired", []))
        if d.get("models") and time.time() - float(d.get("models_t", 0)) < 6 * 3600:
            _cache["models"] = list(d["models"])
            _cache["t"] = time.monotonic() - (time.time() - float(d["models_t"]))
    except Exception:
        pass


def _save_health() -> None:
    try:
        _HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        _HEALTH_FILE.write_text(json.dumps({"lat": _lat, "bad": _bad_until, "nothink": sorted(_nothink),
                                       "retired": sorted(_bad), "models": _cache["models"],
                                       "models_t": time.time() - (time.monotonic() - _cache["t"])}), encoding="utf-8")
    except Exception:
        pass


def _record_latency(name: str, vision: bool, secs: float) -> None:
    k = f"{name}|{'v' if vision else 't'}"
    _lat[k] = secs if k not in _lat else 0.6 * _lat[k] + 0.4 * secs
    _bad_until.pop(name, None)
    _save_health()


def _kid(key: str) -> str:
    """Short, non-reversible id for a key (so health files never hold keys)."""
    import hashlib
    return hashlib.sha1((key or "").encode()).hexdigest()[:6]


_rr = {"n": 0}


def _pairs(names: list, keys: list) -> list:
    """Expand ordered models into (model, key) attempts. Rate limits (429) are per key
    AND per model, so each model is tried with every key that isn't cooling down, and
    the starting key rotates so the load is spread over all of the user's keys."""
    now, wall = time.monotonic(), time.time()
    _rr["n"] += 1
    out = []
    for name in names:
        ks = [k for k in keys if _cool.get(f"{name}|{_kid(k)}", 0) <= now
              and _bad_until.get(f"{name}|{_kid(k)}", 0) <= wall
              and _bad_until.get(f"key|{_kid(k)}", 0) <= wall]
        if ks:
            start = _rr["n"] % len(ks)
            ks = ks[start:] + ks[:start]
        out.extend((name, k) for k in ks)
    return out or [(n, keys[0]) for n in names[:1]]


def _cooldown(name: str, status: int, retry_after: str | None, key: str | None = None) -> None:
    secs = 120.0 if status in (429, 500, 502, 503, 504) else 30.0
    try:
        if retry_after:
            secs = min(max(float(retry_after), 20.0), 600.0)
    except ValueError:
        pass
    if key and status == 429:                  # quota: only this key+model is out
        name = f"{name}|{_kid(key)}"
    _bad_until[name] = time.time() + secs
    _cool[name] = time.monotonic() + secs
    _save_health()


def _key_rejected(key: str) -> None:
    _bad_until[f"key|{_kid(key)}"] = time.time() + 1800
    _save_health()


_load_health()


def _order(cands: list, vision: bool) -> list:
    now = time.monotonic()
    wall = time.time()
    ready = [c for c in cands if _cool.get(c, 0) <= now and _bad_until.get(c, 0) <= wall]  # model-level
    if not ready:
        return sorted(cands, key=lambda c: _bad_until.get(c, 0))
    tag = "v" if vision else "t"
    # Fastest known first; models we have never timed sit at 3 s (so a proven 1.5 s
    # model beats them, and a proven 6 s model loses to them). Ties keep newest-first.
    def guess(c):
        return 2.0 if "lite" in c else (4.0 if "preview" in c else 3.0)
    def cost(c):
        t = _lat.get(f"{c}|{tag}", guess(c))
        # Lite models can place clicks less precisely: for vision they must be
        # clearly faster (2.5x) than a full flash model to be preferred.
        return t * 2.5 if (vision and "lite" in c) else t
    return sorted(ready, key=cost)


async def _candidates(client: httpx.AsyncClient, key: str, requested: str | None) -> list:
    if time.monotonic() - _cache["t"] > 6 * 3600 or not _cache["models"]:
        try:
            r = await client.get(f"{BASE}/models?pageSize=200", headers=_hdr(key), timeout=15)
            if r.status_code == 200:
                _cache["models"] = pick_models(r.json().get("models", []))
                _cache["t"] = time.monotonic()
                _save_health()
        except Exception:
            pass
    order = ([requested] if requested and requested not in ("auto",) else []) + \
            (_cache["models"] or pick_models([]))
    seen, out = set(), []
    for m in order:
        if m and m not in seen and m not in _bad:
            seen.add(m); out.append(m)
    return out[:8]


class GeminiProvider(BaseLLMProvider):

    def __init__(self):
        self._keys = cfg.gemini_keys() or [""]
        self._api_key = self._keys[0]

    async def stream_response(
        self,
        user_text: str,
        screenshots_b64: List[str],
        history: List[Message],
        system_prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        parts: list = []
        for img_b64 in screenshots_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
        parts.append({"text": user_text})
        contents.append({"role": "user", "parts": parts})

        body = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            # Spoken replies and UI grounding don't need long "thinking": turning it
            # off cuts roughly 2-3 s from every response. Dropped if a model rejects it.
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
        }
        # "Thinking" made a one-step screen action take 10-60 s. Plain chat needs none;
        # screenshots get the lowest level (grounding stays accurate, answers in ~2-5 s).
        body["generationConfig"]["thinkingConfig"] = (
            {"thinkingLevel": "low"} if screenshots_b64 else {"thinkingBudget": 0})

        last_err = "no usable Gemini model"
        _vision = bool(screenshots_b64)
        _deadline = time.monotonic() + 45.0     # never keep the user waiting minutes
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=6, read=30)) as client:
            # Google answers 503 "high demand" in short bursts that hit every model
            # at once; a brief backoff and a second pass rides them out.
            for attempt in range(2):
                retriable = False
                queue = _pairs(_order(await _candidates(client, self._api_key, model),
                                      bool(screenshots_b64)), self._keys)[:6]
                while queue:
                    if time.monotonic() > _deadline:
                        raise GeminiError("Gemini is too busy right now. " + last_err[:160])
                    name, key = queue.pop(0)
                    url = f"{BASE}/models/{name}:streamGenerateContent?alt=sse"
                    _t0 = time.monotonic()
                    send = body
                    if name in _nothink and "thinkingConfig" in body["generationConfig"]:
                        send = {**body, "generationConfig": {k: v for k, v in
                                body["generationConfig"].items() if k != "thinkingConfig"}}
                    try:
                        cm = client.stream("POST", url, json=send, headers=_hdr(key))
                        resp = await cm.__aenter__()
                    except httpx.HTTPError as e:
                        last_err = f"{name}: network error {type(e).__name__}"
                        retriable = True
                        _cooldown(name, 0, None)
                        continue
                    try:
                        if os.environ.get("GLANCE_DEBUG_GEMINI"):
                            print(f"[gemini] {name} -> HTTP {resp.status_code} "
                                  f"after {time.monotonic() - _t0:.1f}s", flush=True)
                        if resp.status_code != 200:
                            text = (await resp.aread()).decode("utf-8", "replace")
                            last_err = f"{name}: HTTP {resp.status_code} {_err_text(text, key)}"
                            low = text.lower()
                            if (resp.status_code in (401, 403) and "no longer available" not in low) \
                                    or (resp.status_code == 400 and "api key" in low):
                                _key_rejected(key)               # this key is bad; others may work
                                if not any(_bad_until.get(f"key|{_kid(k)}", 0) <= time.time()
                                           for k in self._keys):
                                    raise GeminiError(last_err)  # every key rejected: stop
                                continue
                            if resp.status_code == 400:
                                if "thinkingConfig" in send["generationConfig"]:
                                    _nothink.add(name); _save_health()   # remember; retry without it
                                    queue.insert(0, (name, key))
                                else:
                                    _bad.add(name); _save_health()  # this model rejects us; skip it
                                continue
                            if resp.status_code in (403, 404):
                                _bad.add(name); _save_health()      # retired for this key
                            elif resp.status_code in (429, 500, 502, 503, 504):
                                if resp.status_code != 429:
                                    retriable = True             # transient; a second pass may work
                                _cooldown(name, resp.status_code, resp.headers.get("retry-after"), key)
                            continue                             # try the next model/key
                        _sticky["vision" if screenshots_b64 else "text"] = name
                        _cool.pop(name, None)
                        _first = True
                        lines = resp.aiter_lines().__aiter__()
                        timed_out = False
                        while True:
                            try:
                                # A model that is up but crawling (30+ s to the first word) is
                                # worse than the next one: give up on it after 14 s.
                                line = await asyncio.wait_for(lines.__anext__(), 14 if _first else 60)
                            except StopAsyncIteration:
                                break
                            except asyncio.TimeoutError:
                                if _first:
                                    timed_out = True
                                    break
                                raise GeminiError(f"{name}: stalled mid-answer")
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if not data or data == "[DONE]":
                                continue
                            try:
                                obj = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            for cand in obj.get("candidates", []):
                                for part in cand.get("content", {}).get("parts", []):
                                    text = part.get("text", "")
                                    if text:
                                        if _first:
                                            _first = False
                                            _record_latency(name, _vision, time.monotonic() - _t0)
                                        yield text
                        if timed_out:
                            _lat[f"{name}|{'v' if _vision else 't'}"] = 20.0
                            last_err = f"{name}: too slow to answer"
                            _cooldown(name, 503, None)
                            retriable = True
                            continue
                        return
                    finally:
                        await cm.__aexit__(None, None, None)
                if not retriable:
                    break
                await asyncio.sleep(1.5 * (attempt + 1))
        if "HTTP 429" in last_err:
            raise GeminiError("Gemini is rate-limiting this key right now (free-tier "
                              "limit). Wait a minute, or enable billing for a higher limit. "
                              f"[{last_err}]")
        if "HTTP 503" in last_err:
            raise GeminiError("Gemini is overloaded right now. Try again in a moment. "
                              f"[{last_err}]")
        raise GeminiError(last_err)

    async def complete(self, user_text: str, screenshots_b64: List[str], history: List[Message],
                       system_prompt: str, model: str | None = None,
                       race: int = 2, budget: float = 40.0) -> str:
        """One full answer, as fast as possible: the best `race` healthy models are asked
        AT THE SAME TIME and the first good answer wins (the rest are cancelled). Free and
        preview Gemini models take 3-20 s at random, so the quickest of two is far steadier
        than one. Failed models are replaced at once by the next candidate; gives up after
        `budget` seconds with a clear error instead of retrying for minutes."""
        contents = [{"role": "user" if m.role == "user" else "model",
                     "parts": [{"text": m.content}]} for m in history]
        parts: list = [{"inline_data": {"mime_type": "image/jpeg", "data": b}}
                       for b in screenshots_b64]
        parts.append({"text": user_text})
        contents.append({"role": "user", "parts": parts})
        vision = bool(screenshots_b64)
        body = {"contents": contents,
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"maxOutputTokens": 512, "temperature": 0.2,
                                     "thinkingConfig": ({"thinkingLevel": "low"} if vision
                                                        else {"thinkingBudget": 0})}}
        loop = asyncio.get_running_loop()
        deadline = loop.time() + budget
        errors: list = []

        async def one(client: httpx.AsyncClient, name: str, key: str) -> str:
            send = body
            if name in _nothink:
                send = {**body, "generationConfig": {k: v for k, v in
                        body["generationConfig"].items() if k != "thinkingConfig"}}
            t0 = time.monotonic()
            for _try in range(2):
                r = await client.post(f"{BASE}/models/{name}:generateContent", json=send,
                                      headers=_hdr(key))
                if r.status_code == 400 and "thinkingConfig" in send["generationConfig"] \
                        and "api key" not in r.text.lower():
                    _nothink.add(name); _save_health()           # drop it for this model
                    send = {**body, "generationConfig": {k: v for k, v in
                            body["generationConfig"].items() if k != "thinkingConfig"}}
                    continue
                break
            if r.status_code != 200:
                low = r.text.lower()
                if (r.status_code in (401, 403) and "no longer available" not in low) \
                        or (r.status_code == 400 and "api key" in low):
                    _key_rejected(key)
                    raise RuntimeError(f"{name}: key rejected (HTTP {r.status_code})")
                if r.status_code in (400, 403, 404):
                    _bad.add(name); _save_health()
                else:
                    _cooldown(name, r.status_code, r.headers.get("retry-after"), key)
                raise RuntimeError(f"{name}: HTTP {r.status_code}")
            try:
                text = "".join(p.get("text", "") for c in r.json().get("candidates", [])
                               for p in c.get("content", {}).get("parts", []))
            except ValueError:
                text = ""
            if not text.strip():
                raise RuntimeError(f"{name}: empty answer")
            _record_latency(name, vision, time.monotonic() - t0)
            return text

        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=6)) as client:
            queue = _pairs(_order(await _candidates(client, self._api_key, model), vision),
                           self._keys)
            # Race DIFFERENT models first (that is what evens out slow ones); the other
            # keys for each model come after as replacements.
            firsts, seen_models = [], set()
            for nm, ky in queue:
                if nm not in seen_models:
                    seen_models.add(nm); firsts.append((nm, ky))
            queue = firsts + [q for q in queue if q not in firsts]
            running: dict = {}
            try:
                while True:
                    while queue and len(running) < race:
                        name, key = queue.pop(0)
                        running[asyncio.ensure_future(one(client, name, key))] = name
                    if not running:
                        break
                    left = deadline - loop.time()
                    if left <= 0:
                        break
                    done, _ = await asyncio.wait(running, timeout=left,
                                                 return_when=asyncio.FIRST_COMPLETED)
                    if not done:
                        break
                    for t in done:
                        name = running.pop(t)
                        exc = t.exception()
                        if exc is None:
                            _sticky["vision" if vision else "text"] = name
                            return t.result()
                        if isinstance(exc, GeminiError):
                            raise exc
                        errors.append(str(exc))
            finally:
                for t in running:
                    t.cancel()
        hint = " Wait a minute and try again, or add a key with billing for higher limits." \
            if any("429" in e or "503" in e for e in errors) else ""
        raise GeminiError("Gemini is too busy right now." + hint +
                          (f" [{errors[-1]}]" if errors else ""))

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{BASE}/models?pageSize=1", headers=_hdr(self._api_key))
                return r.status_code == 200
        except Exception:
            return False
