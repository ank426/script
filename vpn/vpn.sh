#!/usr/bin/env bash
# Wrapper: kill switch is ON only between "vpn up" and "vpn down".
#   vpn up      load kill switch, then connect
#   vpn down    disconnect, then remove kill switch
#   vpn status  show whether the switch and the session are active
#
# If the VPN drops in between, the kill switch stays on and blocks leaks
# until you reconnect (vpn up) or run "vpn down".

set -u

CONFIG="AirVPN_America_UDP-443-Entry3.ovpn"     # imported OpenVPN3 profile name
RULES="$XDG_DATA_HOME/../script/vpn/killswitch.nft"     # nftables ruleset
TABLE="vpnkill"                                 # table name used in the ruleset

switch_on()  { sudo nft -f "$RULES"; }
switch_off() { sudo nft delete table inet "$TABLE" 2>/dev/null || true; }
switch_state() { sudo nft list table inet "$TABLE" >/dev/null 2>&1 && echo on || echo off; }

case "${1:-}" in
  up)
    if [ ! -r "$RULES" ]; then
        echo "Missing ruleset: $RULES" >&2
        exit 1
    fi
    switch_on || { echo "Failed to load kill switch; not connecting." >&2; exit 1; }
    if openvpn3 session-start -c "$CONFIG"; then
        echo "Connected. Kill switch: on"
    else
        echo "Connection failed; removing kill switch." >&2
        switch_off
        exit 1
    fi
    ;;
  down)
    openvpn3 session-manage -c "$CONFIG" --disconnect || true
    switch_off
    echo "Disconnected. Kill switch: off"
    ;;
  status)
    echo "Kill switch: $(switch_state)"
    openvpn3 sessions-list
    ;;
  *)
    echo "Usage: ${0##*/} {up|down|status}" >&2
    exit 2
    ;;
esac
