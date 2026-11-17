#!/bin/bash
cd /home/jason/shopify-admin
nohup .venv/bin/python deploy/_diag_backfill538.py > /tmp/diag538.log 2>&1 &
echo started pid=$!
