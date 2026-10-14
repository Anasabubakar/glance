"""Glance Cloud registrar: mints a rate-limited LiteLLM virtual key per install.
Listens on 127.0.0.1:8090; Caddy routes POST /register here. Stdlib only.

Limits are deliberately modest: the free tier is one CPU box. Signups are limited
per IP per day (shared networks such as offices and campuses share an IP, so this
is not tiny), and each key is limited per minute and to 2 requests in flight.
"""
import json, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LITELLM = "http://127.0.0.1:4000"
MASTER = os.environ["LITELLM_MASTER_KEY"]
PER_IP_PER_DAY = 40
RPM, PARALLEL, TPM = 20, 2, 40000
_seen: dict[str, list[float]] = {}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/register":
            return self._send(404, {"error": "not found"})
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        now = time.time()
        hits = [t for t in _seen.get(ip, []) if now - t < 86400]
        if len(hits) >= PER_IP_PER_DAY:
            return self._send(429, {"error": "too many registrations from this address"})
        hits.append(now)
        _seen[ip] = hits
        req = urllib.request.Request(
            f"{LITELLM}/key/generate",
            data=json.dumps({"models": ["glance"], "rpm_limit": RPM, "tpm_limit": TPM,
                             "max_parallel_requests": PARALLEL, "duration": "90d",
                             "metadata": {"source": "glance-register"}}).encode(),
            headers={"Authorization": f"Bearer {MASTER}", "Content-Type": "application/json"})
        try:
            key = json.load(urllib.request.urlopen(req, timeout=15))["key"]
        except Exception:
            return self._send(502, {"error": "upstream unavailable"})
        self._send(200, {"api_key": key, "base_url": "https://llm.anasmasama.dev/v1",
                         "model": "glance", "rpm": RPM})

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", 8090), H).serve_forever()
