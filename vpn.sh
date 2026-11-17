#!/usr/bin/env bash
# VPN control through NetworkManager (no sudo needed).
# Install as ~/.local/bin/vpn (mode 755).
#
#   vpn up      connect (the dispatcher script loads the kill switch)
#   vpn down    disconnect on purpose (the dispatcher script removes the kill switch)
#   vpn status  connection state and public IP

set -u

CONN="AirVPN_America_UDP-443-Entry3"   # NetworkManager connection name (nmcli connection show)
FLAG="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/vpn-intentional-down"

is_active() { nmcli -t -f NAME connection show --active | grep -qx "$CONN"; }

case "${1:-}" in
  up)
    rm -f "$FLAG"
    nmcli connection up "$CONN"
    ;;
  down)
    killall qbittorrent-nox
    if is_active; then
        touch "$FLAG"                    # tells the dispatcher this disconnect is intentional
        nmcli connection down "$CONN"
        echo "Disconnected."
    else
        rm -f "$FLAG"
        echo "VPN is not active."
        # NM fires no vpn-down for an already-inactive connection, so the
        # dispatcher can never clear a leftover kill switch here. Do it now.
        if sudo -n nft delete table inet vpnkill 2>/dev/null; then
            echo "Removed leftover kill switch."
        else
            echo "If your internet is still blocked, remove the leftover kill switch with:"
            echo "  sudo nft delete table inet vpnkill"
        fi
    fi
    ;;
  status)
    if is_active; then echo "VPN: connected"; else echo "VPN: not connected"; fi
    echo -n "Public IPv4: "; curl -4 -s --max-time 5 https://api.ipify.org || echo "unreachable"
    echo
    ;;
  *)
    echo "Usage: ${0##*/} {up|down|status}" >&2
    exit 2
    ;;
esac
