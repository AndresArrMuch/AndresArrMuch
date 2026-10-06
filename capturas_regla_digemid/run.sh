#!/bin/bash
# run.sh main|rama PORT [script]
TAG=$1; PORT=$2; SCRIPT=${3:-regla_test.py}
case $TAG in main) B=/tmp/claude-0/wt_main/backend;; rama) B=/tmp/claude-0/wt_ser/backend;; esac
DB=regla_${TAG}_${SCRIPT%.py}; LOG=/tmp/claude-0/repro/regla/nube_${TAG}_${SCRIPT%.py}.jsonl
rm -f $LOG $LOG.mode $LOG.occupy
cd /tmp && su postgres -c "psql -p 5433 -qc 'DROP DATABASE IF EXISTS $DB' -c 'CREATE DATABASE $DB TEMPLATE igbase'" >/dev/null 2>&1
cd /tmp/claude-0/repro/regla
/tmp/claude-0/venv/bin/python serve_regla.py $B "postgresql://postgres@/$DB?host=/var/run/postgresql&port=5433" $PORT $LOG > srv_${TAG}_${SCRIPT%.py}.log 2>&1 &
SRV=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:$PORT/erp && break; sleep 1; done
/tmp/claude-0/venv/bin/python $SCRIPT $PORT $DB $LOG $TAG > out_${TAG}_${SCRIPT%.py}.txt 2>&1
kill $SRV
