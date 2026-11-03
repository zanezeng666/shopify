#!/bin/bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.estrybattery.com/" -o /tmp/home2.html
wc -c /tmp/home2.html
echo "--- hero title ---"
grep -o 'esh__title{[^}]*}' /tmp/home2.html | head -1
grep -o 'esh__kicker{[^}]*}' /tmp/home2.html | head -1
echo "--- category ---"
grep -o 'ecg__title{[^}]*}' /tmp/home2.html | head -1
grep -o 'ecg__count{[^}]*}' /tmp/home2.html | head -1
echo "--- trust bar ---"
grep -o 'etb__txt strong{[^}]*}' /tmp/home2.html | head -1
grep -o 'etb__txt span{[^}]*}' /tmp/home2.html | head -1
echo "--- how it works ---"
grep -o 'ehw__title{[^}]*}' /tmp/home2.html | head -1
grep -o 'ehw__sd{[^}]*}' /tmp/home2.html | head -1
grep -o 'ehw__st{[^}]*}' /tmp/home2.html | head -1
echo "--- font-heading-family root ---"
grep -o -- '--font-heading-family:[^;]*;' /tmp/home2.html | head -1
