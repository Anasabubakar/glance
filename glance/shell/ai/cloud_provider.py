"""Glance Cloud: a free hosted text model, so new users need no local download
and no API key. On first use the app mints a rate-limited key from the registrar
and caches it (in a plain file next to the user's .env, so it survives restarts
even if the .env can't be written). Text-only: screenshots are not uploaded (use a
BYOK vision model or local Ollama for screen-aware features)."""

import json
import os
import urllib.error
import urllib.request

from ai.custom_provider import CustomProvider
from config import cfg, _USER_DIR


class CloudUnavailable(RuntimeError):
    """The free tier can't be used right now (friendly message for the user)."""


def _key_file():
    return _USER_DIR / "cloud_key"


def _read_cached_key() -> str:
    if cfg.cloud_key:
        return cfg.cloud_key
    try:
        k = _key_file().read_text(encoding="utf-8").strip()
        if k:
            cfg.cloud_key = k
            os.environ["GLANCE_CLOUD_KEY"] = k
        return k
    except OSError:
        return ""


def ensure_cloud_key() -> str:
    """Return the cached cloud key, minting (and saving) one on first use."""
    key = _read_cached_key()
    if key:
        return key
    req = urllib.request.Request(f"{cfg.cloud_url}/register", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            key = json.loads(resp.read())["api_key"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise CloudUnavailable(
                "Glance Cloud has hit its free sign-up limit for today. Try again "
                "later, or add your own key under API Keys → Custom endpoint.") from e
        raise CloudUnavailable(f"Glance Cloud is unavailable (HTTP {e.code}).") from e
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        raise CloudUnavailable(
            "Can't reach Glance Cloud. Check your internet connection, or add your "
            "own key under API Keys → Custom endpoint.") from e
    cfg.cloud_key = key
    os.environ["GLANCE_CLOUD_KEY"] = key
    try:
        _key_file().parent.mkdir(parents=True, exist_ok=True)
        _key_file().write_text(key, encoding="utf-8")
        _key_file().chmod(0o600)
    except OSError:
        pass                      # still works this session; also try the .env
    cfg._persist_env("GLANCE_CLOUD_KEY", key)
    return key


class CloudProvider(CustomProvider):
    send_images = False
    max_retries = 6      # shared free tier: one slot, so wait our turn instead of failing
    max_tokens = 220     # spoken replies are short; fewer tokens = faster on CPU

    def __init__(self):
        super().__init__(base_url=f"{cfg.cloud_url}/v1",
                         api_key=ensure_cloud_key(), model="glance")
