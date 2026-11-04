#!/bin/bash
# ui_run.sh main|cob PORT
B=/tmp/claude-0/wt_$1/backend; D=/tmp/claude-0/repro/cob/ui_$1.db
cd /tmp/claude-0/repro/cob && CID=$(BACK=$B DBP=$D /tmp/claude-0/venv/bin/python ui_db.py 2>/dev/null | tail -1)
/tmp/claude-0/venv/bin/python /tmp/claude-0/repro/req/serve_req.py $B $D $2 /tmp/claude-0/repro/cob/ng_$1.log > /tmp/claude-0/repro/cob/srv_$1.log 2>&1 &
SRV=$!
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:$2/erp && break; sleep 1; done
node ui_cob.js $2 $1 $CID
kill $SRV
