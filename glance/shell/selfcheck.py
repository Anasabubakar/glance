"""
selfcheck.py — a one-click checkup of everything Glance needs, with plain results.

Each check returns (name, ok, detail). Nothing here changes any setting, and nothing
prints a key: it is meant to be pasted into a bug report.
"""

from __future__ import annotations

import asyncio
import sys
import time

from config import cfg


def _gnome_checks() -> list:
    out = []
    try:
        from screen import gnome_bridge as gb
    except Exception:
        return out
    if not sys.platform.startswith("linux"):
        return out
    if gb.available():
        out.append(("GNOME extension", True, "loaded and up to date"))
        t = time.monotonic()
        shots = None
        try:
            from screen.capture import capture_all_screens
            shots = capture_all_screens()
        except Exception as e:
            out.append(("Screen capture", False, type(e).__name__))
        if shots is not None:
            out.append(("Screen capture", bool(shots),
                        f"{len(shots)} screen(s), {time.monotonic() - t:.1f}s" if shots else "blank frame"))
        if gb.supports_windows():
            n = len(gb.windows())
            out.append(("Windows control", n > 0, f"{n} windows visible"))
        else:
            out.append(("Windows control", False, "log out and back in once to enable instant window commands"))
    elif gb.outdated():
        out.append(("GNOME extension", False, "an old copy is loaded: log out and back in once"))
    else:
        out.append(("GNOME extension", False, "not running (needed for screen capture and clicks on Wayland)"))
    return out


def _audio_checks() -> list:
    out = []
    try:
        import sounddevice as sd
        ins = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
        out.append(("Microphone", bool(ins), f"{len(ins)} input device(s)" if ins else "none found"))
    except Exception as e:
        out.append(("Microphone", False, type(e).__name__))
    out.append(("Speech to text", True, cfg.stt_provider()))
    out.append(("Voice (text to speech)", True, cfg.tts_provider()))
    return out


async def _ping(name: str) -> tuple:
    from ai.fallback_provider import FallbackProvider
    t = time.monotonic()
    try:
        text = ""
        prov = FallbackProvider([name], log=lambda m: None)
        async for c in prov.stream_response("Reply with the single word OK.", [], [],
                                            "You are a connectivity test. Reply with one word."):
            text += c
            if text.strip():
                break
        ms = (time.monotonic() - t) * 1000
        return (f"AI: {name}", bool(text.strip()), f"answered in {ms:.0f} ms")
    except Exception as e:
        msg = str(e)[:90].replace("\n", " ")
        return (f"AI: {name}", False, f"{type(e).__name__}: {msg}")


def _ai_checks() -> list:
    order = cfg.provider_order()
    if not order:
        return [("AI providers", False, "none set up: add one under AI & Keys")]
    out = []
    for name in order:
        if name in ("ollama", "copilot", "custom", "cloud"):
            out.append((f"AI: {name}", True, "configured (not pinged)"))
            continue
        try:
            out.append(asyncio.run(asyncio.wait_for(_ping(name), 25)))
        except Exception as e:
            out.append((f"AI: {name}", False, type(e).__name__))
    keys = {p: len(cfg.keys_for(p)) for p in cfg.KEYED if cfg.keys_for(p)}
    if keys:
        out.append(("API keys", True, ", ".join(f"{p}: {n}" for p, n in keys.items())))
    return out


def _accuracy_checks() -> list:
    try:
        from ai.grounding import is_stale, load_scores
        sc = load_scores()
        if not sc:
            return [("Click accuracy", True, "not measured yet (Glance measures it in the background)")]
        best = max(sc, key=sc.get)
        return [("Click accuracy", sc[best] >= 0.6,
                 f"best model {best}: {sc[best]:.0%} of test clicks hit" + (" (old)" if is_stale() else ""))]
    except Exception as e:
        return [("Click accuracy", False, type(e).__name__)]


def _command_checks() -> list:
    try:
        from localcmd import parse
        ok = parse("minimize this window") is not None and parse("open the calculator") is not None
        return [("Instant commands", ok, "window, app, volume and key commands need no AI")]
    except Exception as e:
        return [("Instant commands", False, type(e).__name__)]


def run_checks() -> list:
    out: list = []
    for fn in (_gnome_checks, _audio_checks, _command_checks, _accuracy_checks, _ai_checks):
        try:
            out += fn()
        except Exception as e:
            out.append((fn.__name__.strip("_"), False, f"{type(e).__name__}: {e}"))
    return out


def format_report(checks: list) -> str:
    from secrets_redact import redact
    lines = ["--- Checkup ---"]
    for name, ok, detail in checks:
        lines.append(f"{'PASS' if ok else 'FAIL'}  {name:<24} {detail}")
    bad = [c for c in checks if not c[1]]
    lines.append("")
    lines.append("Everything looks good." if not bad else f"{len(bad)} thing(s) need attention (marked FAIL).")
    return redact("\n".join(lines))
