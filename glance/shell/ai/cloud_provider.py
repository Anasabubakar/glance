"""Glance Cloud: a free hosted text model, so new users need no local download
and no API key. On first use the app mints a rate-limited key from the registrar
and caches it in the user's .env. Text-only: screenshots are not uploaded (use a
BYOK vision model or local Ollama for screen-aware features)."""

import json
import os
import urllib.request

from ai.custom_provider import CustomProvider
from config import cfg


def ensure_cloud_key() -> str:
    """Return the cached cloud key, minting one on first use."""
    if cfg.cloud_key:
        return cfg.cloud_key
    req = urllib.request.Request(f"{cfg.cloud_url}/register", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        key = json.loads(resp.read())["api_key"]
    cfg.cloud_key = key
    os.environ["GLANCE_CLOUD_KEY"] = key
    cfg._persist_env("GLANCE_CLOUD_KEY", key)
    return key


class CloudProvider(CustomProvider):
    send_images = False
    max_retries = 6      # shared free tier: one slot, so wait our turn instead of failing

    def __init__(self):
        super().__init__(base_url=f"{cfg.cloud_url}/v1",
                         api_key=ensure_cloud_key(), model="glance")
