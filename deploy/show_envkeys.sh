#!/bin/bash
cd /home/jason/shopify-admin
sed -E "s/=.{6}.*/=***/" .env | grep -vE "^\s*(#|$)"
