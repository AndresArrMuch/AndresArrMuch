#!/bin/bash
TAG=$1; PORT=$2
case $TAG in main) B=/tmp/claude-0/wt_main/backend;; rama) B=/tmp/claude-0/wt_ser/backend;; esac
DB=regla_ui_$TAG; LOG=/tmp/claude-0/repro/regla/nube_ui_$TAG.jsonl; rm -f $LOG $LOG.mode
cd /tmp && su postgres -c "psql -p 5433 -qc 'DROP DATABASE IF EXISTS $DB' -c 'CREATE DATABASE $DB TEMPLATE igbase'" >/dev/null 2>&1
cd /tmp/claude-0/repro/regla
/tmp/claude-0/venv/bin/python serve_regla.py $B "postgresql://postgres@/$DB?host=/var/run/postgresql&port=5433" $PORT $LOG > srv_ui_$TAG.log 2>&1 &
SRV=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:$PORT/erp && break; sleep 1; done
read COT_DIG COT_MIX < <(/tmp/claude-0/venv/bin/python -c "
import sys; sys.argv=['x','$PORT','$DB','$LOG','$TAG']
exec(open('regla_test.py').read().split(\"setmode('ok')\nRUTAS\")[0])
print(cot([L(DIG,'PAR')]), cot([L(DIG,'PAR'), L(N1,'NIU')]))")
node ui_regla.js $PORT $TAG $LOG $COT_DIG $COT_MIX > ui_$TAG.txt 2>&1
kill $SRV
