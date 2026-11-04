#!/bin/bash
# vol_run.sh <worktree> <tag> <port>
B=$1/backend; DBP='postgresql://postgres@/digvol?host=/var/run/postgresql&port=5433'
CID=$(/tmp/claude-0/venv/bin/python -c "import json;print(json.load(open('/tmp/claude-0/repro/dig/ids.json'))['CID'])")
cd /tmp/claude-0/repro/dig && /tmp/claude-0/venv/bin/python serve_vol.py $B "$DBP" $3 > srv_vol_$2.log 2>&1 &
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:$3/erp && break; sleep 1; done
node ui_vol.js $3 $2 $CID /tmp/claude-0/repro/dig/$2 > /tmp/claude-0/repro/dig/vol_$2.txt 2>&1; kill %1
