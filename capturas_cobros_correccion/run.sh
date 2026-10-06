#!/bin/bash
# run.sh main|rama CASO
case $1 in main) B=/tmp/claude-0/wt_main/backend;; rama) B=/tmp/claude-0/wt_cob/backend;; esac
cd /tmp/claude-0/repro/cob && BACK=$B DBP=/tmp/claude-0/repro/cob/$1_$2.db JAN_FIRST=1 MODO=$1 CASO=$2 /tmp/claude-0/venv/bin/python cob_test.py 2>&1 | grep '^{' 
