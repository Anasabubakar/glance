"""
Grounding benchmark (used by Glance to choose accurate vision models): can a model click the right thing?

Draws synthetic "screenshots" (window with title-bar buttons, toolbar, list, form) where
every control's true position is known, asks each Gemini model to click one by name
(using the same normalized 0-1000 grid Glance uses) and scores hits and latency.
Results are saved to ~/.glance/grounding.json; Glance uses them to avoid models that
miss and to prefer ones that are both accurate and fast.

    python tools/grounding_bench.py [--trials 8] [--models a,b,c]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import httpx  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from ai.gemini_provider import BASE, _hdr  # noqa: E402
from config import cfg  # noqa: E402

W, H = 1366, 768
LABELS = ["Save", "Open", "Print", "Share", "Export", "Settings", "Help", "Undo", "Search", "Upload",
          "Download", "Delete", "Refresh", "Compose", "Archive", "Reports", "Profile", "Billing"]
SYS = ('You control a screen. Reply ONLY JSON {"action":"click","x":N,"y":N,"text":"..."}. '
       "Coordinates use a normalized 1000x1000 grid over the whole screenshot: x=0 is the left edge, "
       "x=1000 the right edge, y=0 the top, y=1000 the bottom. Aim at the CENTER of the target.")


def _font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def make_scene(rng: random.Random):
    """A fake app window. Returns (png_bytes, {label: (x0, y0, x1, y1)})."""
    img = Image.new("RGB", (W, H), rng.choice([(236, 236, 240), (30, 32, 38), (250, 248, 244)]))
    d = ImageDraw.Draw(img)
    dark = sum(img.getpixel((5, 5))) < 300
    fg = (235, 235, 240) if dark else (30, 30, 36)
    f = _font(18)
    wx0, wy0 = rng.randint(40, 200), rng.randint(40, 120)
    wx1, wy1 = W - rng.randint(40, 200), H - rng.randint(30, 80)
    d.rectangle([wx0, wy0, wx1, wy1], fill=(58, 60, 68) if dark else (255, 255, 255), outline=(120, 120, 130))
    d.rectangle([wx0, wy0, wx1, wy0 + 40], fill=(44, 46, 52) if dark else (222, 222, 228))
    boxes = {}
    for i, (name, col) in enumerate((("Minimize", (240, 190, 50)), ("Maximize", (60, 200, 90)), ("Close", (235, 80, 80)))):
        cx = wx1 - 28 - 34 * (2 - i) + 0
        cy = wy0 + 20
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=col)
        boxes[f"{name} button"] = (cx - 12, cy - 12, cx + 12, cy + 12)
    labels = rng.sample(LABELS, 8)
    x = wx0 + 24
    y = wy0 + 70
    for lab in labels:
        w = int(d.textlength(lab, font=f)) + 36
        if x + w > wx1 - 20:
            x = wx0 + 24
            y += 70
        d.rounded_rectangle([x, y, x + w, y + 40], radius=8, fill=(90, 120, 230), outline=(60, 90, 200))
        d.text((x + 18, y + 9), lab, fill=(255, 255, 255), font=f)
        boxes[f"{lab} button"] = (x, y, x + w, y + 40)
        x += w + 20
    for i in range(3):                                   # distractor text rows
        d.text((wx0 + 30, wy1 - 150 + i * 36), f"Item {i + 1}  ·  {rng.choice(LABELS)} notes", fill=fg, font=f)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue(), boxes


async def ask(client, key, model, jpeg, label):
    body = {"contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                {"text": f"click the {label}"}]}],
            "systemInstruction": {"parts": [{"text": SYS}]},
            "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1,
                                 "thinkingConfig": {"thinkingLevel": "low"}}}
    t = time.monotonic()
    try:
        r = await client.post(f"{BASE}/models/{model}:generateContent", json=body, headers=_hdr(key))
        if r.status_code == 400 and "thinking" in r.text.lower():
            body["generationConfig"].pop("thinkingConfig")
            r = await client.post(f"{BASE}/models/{model}:generateContent", json=body, headers=_hdr(key))
    except httpx.HTTPError:
        return None, time.monotonic() - t, 0          # timed out: counts as an error
    dt = time.monotonic() - t
    if r.status_code != 200:
        return None, dt, r.status_code
    txt = "".join(p.get("text", "") for c in r.json().get("candidates", []) for p in c.get("content", {}).get("parts", []))
    m = re.search(r'"x"\s*:\s*(\d+).*?"y"\s*:\s*(\d+)', txt, re.S)
    return ((int(m.group(1)) / 1000 * W, int(m.group(2)) / 1000 * H) if m else None), dt, 200


def crop_around(jpeg: bytes, pt, frac=0.16):
    """A zoomed crop centred on the first guess: (jpeg_bytes, (x0, y0, w, h))."""
    im = Image.open(io.BytesIO(jpeg)).convert("RGB")
    cw, ch = int(W * frac * 2), int(H * frac * 2)
    x0 = int(min(max(pt[0] - cw / 2, 0), W - cw))
    y0 = int(min(max(pt[1] - ch / 2, 0), H - ch))
    c = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((cw * 2, ch * 2), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    c.save(buf, "JPEG", quality=88)
    return buf.getvalue(), (x0, y0, cw, ch)


async def ask_refined(client, key, model, jpeg, label):
    """Two steps: coarse guess on the whole screen, then re-aim inside a zoomed crop."""
    pt, dt1, st = await ask(client, key, model, jpeg, label)
    if st != 200 or pt is None:
        return pt, dt1, st
    cj, (x0, y0, cw, ch) = crop_around(jpeg, pt)
    p2, dt2, st2 = await ask_crop(client, key, model, cj, label, (x0, y0, cw, ch))
    return (p2 or pt), dt1 + dt2, 200


async def ask_crop(client, key, model, cj, label, box):
    body = {"contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(cj).decode()}},
                {"text": f"click the {label}"}]}],
            "systemInstruction": {"parts": [{"text": SYS}]},
            "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1,
                                 "thinkingConfig": {"thinkingLevel": "low"}}}
    t = time.monotonic()
    try:
        r = await client.post(f"{BASE}/models/{model}:generateContent", json=body, headers=_hdr(key))
        if r.status_code == 400 and "thinking" in r.text.lower():
            body["generationConfig"].pop("thinkingConfig")
            r = await client.post(f"{BASE}/models/{model}:generateContent", json=body, headers=_hdr(key))
    except httpx.HTTPError:
        return None, time.monotonic() - t, 0
    if r.status_code != 200:
        return None, time.monotonic() - t, r.status_code
    txt = "".join(p.get("text", "") for c in r.json().get("candidates", []) for p in c.get("content", {}).get("parts", []))
    m = re.search(r'"x"\s*:\s*(\d+).*?"y"\s*:\s*(\d+)', txt, re.S)
    x0, y0, cw, ch = box
    return ((x0 + int(m.group(1)) / 1000 * cw, y0 + int(m.group(2)) / 1000 * ch) if m else None), time.monotonic() - t, 200


async def bench(models, trials, refine=False, progress=None):
    keys = cfg.gemini_keys()
    if not keys:
        sys.exit("No Gemini key configured.")
    rng = random.Random(7)
    scenes = [make_scene(rng) for _ in range(trials)]
    results = {}
    async with httpx.AsyncClient(timeout=25) as client:
        for model in models:
            hits = n = errs = 0
            lats = []
            for i, (jpeg, boxes) in enumerate(scenes):
                label = rng.choice(list(boxes))
                x0, y0, x1, y1 = boxes[label]
                fn = ask_refined if refine else ask
                pt, dt, status = await fn(client, keys[i % len(keys)], model, jpeg, label)
                if status != 200:
                    errs += 1
                    continue
                n += 1
                lats.append(dt)
                if pt and x0 - 6 <= pt[0] <= x1 + 6 and y0 - 6 <= pt[1] <= y1 + 6:
                    hits += 1
            acc = hits / n if n else 0.0
            lat = sum(lats) / len(lats) if lats else 0.0
            results[model] = {"accuracy": round(acc, 2), "latency": round(lat, 2), "trials": n, "errors": errs}
            line = f"{model:34s} accuracy {acc:4.0%}  latency {lat:4.1f}s  ({n} ok, {errs} errors)"
            print(line, flush=True)
            if progress:
                progress(line)
    if not refine:      # only the plain single-call scores steer Glance's model choice
        out = Path.home() / ".glance" / "grounding.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"t": time.time(), "results": results}, indent=1))
    return results




GROUNDING_FILE = Path.home() / ".glance" / "grounding.json"


def load_scores() -> dict:
    """{model: accuracy 0..1} from the last calibration (empty if never run)."""
    try:
        return {k: float(v.get("accuracy", 0)) for k, v in
                json.loads(GROUNDING_FILE.read_text()).get("results", {}).items() if v.get("trials", 0) >= 3}
    except Exception:
        return {}


def is_stale(days: float = 14.0) -> bool:
    try:
        return time.time() - float(json.loads(GROUNDING_FILE.read_text()).get("t", 0)) > days * 86400
    except Exception:
        return True


async def calibrate(trials: int = 5, top: int = 5, progress=None) -> dict:
    """Score the top Gemini models; saves ~/.glance/grounding.json."""
    from ai.gemini_provider import _candidates
    async with httpx.AsyncClient(timeout=15) as c:
        models = (await _candidates(c, cfg.gemini_keys()[0], None))[:top]
    return await bench(models, trials, False, progress)
