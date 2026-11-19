#!/bin/bash
# traffic-web 双层看板部署冒烟
systemctl restart traffic-web
sleep 4
echo "service: $(systemctl is-active traffic-web)"
K=$(grep '^TRAFFIC_KEY=' /home/jason/shopify-admin/.env | cut -d= -f2)
echo "--- /api/realtime (head) ---"
curl -s "http://127.0.0.1:8010/api/realtime?k=$K" | head -c 700
echo
echo "--- /api/day status ---"
curl -s -o /dev/null -w "day HTTP %{http_code}, %{time_total}s\n" "http://127.0.0.1:8010/api/day?date=today&k=$K"
echo "--- page realtime block ---"
curl -s "http://127.0.0.1:8010/?k=$K" | grep -c -E 'rtcards|rtgeo|loadRT'
echo "--- https (nginx path) ---"
curl -s -o /dev/null -w "https HTTP %{http_code}\n" "https://api.bornmieo.com/traffic/api/realtime?k=$K"
