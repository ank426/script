#!/bin/sh

set -e

MAC_ADDRESS=14:0B:9E:F9:9B:60
trap 'echo; nmcli device disconnect $MAC_ADDRESS || true' EXIT
nmcli device connect $MAC_ADDRESS
scroll --qr --iface enp0s20f0u10 $@
