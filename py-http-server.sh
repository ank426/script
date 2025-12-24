#!/bin/sh

ip=$(ip -json -4 -brief address | jq -r '.[] | select(.ifname == "wlo1") | .addr_info[0].local')
port=8000
qrencode -t ansiutf8 "http://$ip:$port"
python -m http.server
