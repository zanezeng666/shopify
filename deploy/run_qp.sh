#!/bin/bash
PY=$(ls /home/jason/shopify-admin/.venv/bin/python 2>/dev/null || ls /home/jason/shopify-admin/venv/bin/python 2>/dev/null || echo python3)
$PY /tmp/query_plan.py
