import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import secrets_redact as sr  # noqa: E402


def test_configured_and_lookalike_keys_are_masked(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "ZZtopSecretValue1234567890")
    monkeypatch.setenv("GROQ_API_KEYS", "second-secret-key-abcdef123456")
    out = sr.redact("a ZZtopSecretValue1234567890 b second-secret-key-abcdef123456 c")
    assert "ZZtopSecretValue1234567890" not in out and "second-secret-key" not in out
    for sample in ("AIzaSyA1234567890abcdefghijklmnop", "sk-abcdefghijklmnopqrstuvwx1234",
                   "gsk_abcdefghijklmnopqrstuvwx", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123"):
        masked = sr.redact(sample)
        assert masked != sample and "abcdefghijklmnopqrstuvwx" not in masked.replace("[key", "")
    assert sr.redact("hello world") == "hello world"
