#!/bin/bash
# Updates the Glance Cloud server on the VPS:
#   * installs the current registrar.py (higher signup limit) and restarts it,
#     which also clears the in-memory daily signup counters;
#   * lets the shared model queue up to 4 requests instead of rejecting the 2nd
#     concurrent one with HTTP 429 (Ollama still runs them one at a time);
#   * restarts LiteLLM to pick that up.
# Usage:  GLANCE_VPS_KEY=/path/to/ssh_key GLANCE_VPS_HOST=user@host \
#           bash server/glance-cloud/update.sh
set -e
: "${GLANCE_VPS_KEY:?set GLANCE_VPS_KEY to your SSH private key path}"
: "${GLANCE_VPS_HOST:?set GLANCE_VPS_HOST to user@host}"
KEY=$GLANCE_VPS_KEY
HOST=$GLANCE_VPS_HOST
HERE="$(cd "$(dirname "$0")" && pwd)"
scp -i "$KEY" -o IdentitiesOnly=yes "$HERE/registrar.py" $HOST:/tmp/registrar.py
ssh -i "$KEY" -o IdentitiesOnly=yes $HOST 'set -e
sudo cp /tmp/registrar.py /opt/glance-registrar/registrar.py
sudo systemctl restart glance-registrar
cd /opt/gateway
cp config.yaml config.yaml.bak2
python3 - <<"PY"
import re
p = "config.yaml"; s = open(p).read()
s2 = re.sub(r"(model_name: glance(?:.|\n)*?max_parallel_requests:\s*)\d+", r"\g<1>4", s, count=1)
open(p, "w").write(s2)
print("config.yaml updated" if s2 != s else "config.yaml already up to date")
PY
sudo docker compose restart litellm >/dev/null 2>&1
sleep 20
systemctl is-active glance-registrar'
echo "--- test: register + one completion"
KEYJ=$(curl -s -X POST https://llm.anasmasama.dev/register -d '{}')
echo "$KEYJ" | python3 -c "import json,sys; d=json.load(sys.stdin); print('registered, rpm limit =', d['rpm'])"
K=$(echo "$KEYJ" | python3 -c "import json,sys; print(json.load(sys.stdin)['api_key'])")
curl -s -m 120 https://llm.anasmasama.dev/v1/chat/completions -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
  -d '{"model":"glance","messages":[{"role":"user","content":"Say OK"}],"max_tokens":8}' | head -c 300; echo
