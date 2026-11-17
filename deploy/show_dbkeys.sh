#!/bin/bash
cd /home/jason/shopify-admin
grep -iE "^(DB|MYSQL|DATABASE)" .env | sed -E "s/(PASS\w*=.{4}).*/\1***/"
