#!/bin/sh

pgrep -x weylus > /dev/null && killall weylus
wp=1701
# ip=$(ip -json -4 -brief address | jq -r '.[] | select(.ifname == "wlo1") | .addr_info[0].local')
ip=ankit
ac=$(head --bytes=20 /dev/urandom | base32)
qrencode -t ansiutf8 "http://$ip:$wp?access_code=$ac"
weylus --no-gui --access-code "$ac" --web-port $wp
