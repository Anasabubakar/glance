"""
Pick a working Gemini model at runtime.

Google retires model names often and tells new keys "no longer available to new
users", so a hardcoded name goes stale (it broke Glance: HTTP 404 on every
request). Instead we ask Google which models the key can use and prefer the
newest stable *flash* model, with the `-latest` aliases and lite models as
fallbacks.
"""

import re

_EXCLUDE = re.compile(
    r"image|tts|audio|live|embed|robotics|computer-use|thinking|exp|preview|omni|"
    r"antigravity|gemma|learnlm|aqa|imagen|veo|nano|vision-only", re.I)
_FLASH = re.compile(r"^gemini-(\d+(?:\.\d+)?)-flash$")
_LITE = re.compile(r"^gemini-(\d+(?:\.\d+)?)-flash-lite$")


def _ver(name: str, rx) -> float:
    m = rx.match(name)
    return float(m.group(1)) if m else -1.0


def pick_models(models: list) -> list:
    """Ordered candidates from a ListModels `models` array. Newest stable flash
    first, then gemini-flash-latest, then lite models."""
    names = []
    for m in models or []:
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        n = (m.get("name") or "").split("/")[-1]
        if n and not _EXCLUDE.search(n):
            names.append(n)
    flash = sorted((n for n in names if _FLASH.match(n)), key=lambda n: _ver(n, _FLASH), reverse=True)
    lite = sorted((n for n in names if _LITE.match(n)), key=lambda n: _ver(n, _LITE), reverse=True)
    if not names:                       # list unavailable: the aliases always resolve
        return ["gemini-flash-latest", "gemini-flash-lite-latest"]
    # Top two flash models, then the always-valid alias, then older flash, then lite.
    out = list(flash[:2])
    if "gemini-flash-latest" in names or not names:
        out.append("gemini-flash-latest")
    out += flash[2:] + lite
    if "gemini-flash-lite-latest" in names:
        out.append("gemini-flash-lite-latest")
    return out or ["gemini-flash-latest", "gemini-flash-lite-latest"]
