#!/bin/bash
# ui_run.sh main|dig PORT
B=/tmp/claude-0/wt_$1/backend; DBP='postgresql://postgres@/digemid?host=/var/run/postgresql&port=5433'
CID=$(/tmp/claude-0/venv/bin/python -c "import json;print(json.load(open('/tmp/claude-0/repro/dig/ids.json'))['CID'])")
cd /tmp/claude-0/repro/dig && /tmp/claude-0/venv/bin/python serve_dig.py $B "$DBP" $2 > srv_$1.log 2>&1 &
SRV=$!
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:$2/erp && break; sleep 1; done
node ui_dig.js $2 $1 $CID /tmp/claude-0/repro/dig/$1
kill $SRV
