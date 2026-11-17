#!/bin/bash
cd /home/jason/shopify-admin
get(){ grep -E "^$1=" .env | head -1 | cut -d= -f2 | tr -d ' "'; }
DBPASS=$(get SHOPIFY_DB_PASSWORD); DBUSER=$(get SHOPIFY_DB_USER)
DBNAME=$(get SHOPIFY_DB_NAME); DBHOST=$(get SHOPIFY_DB_HOST); DBPORT=$(get SHOPIFY_DB_PORT); DBPORT=${DBPORT:-3306}
echo "host=$DBHOST port=$DBPORT user=$DBUSER db=$DBNAME pass_len=${#DBPASS}"
mysql -h$DBHOST -P$DBPORT -u$DBUSER -p"$DBPASS" $DBNAME -e "show tables" 2>&1 | head -25
