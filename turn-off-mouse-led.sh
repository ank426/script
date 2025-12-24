#!/bin/sh

DEVICE_NAME="G102"
VENDOR="046d"
PRODUCT="c092"

EVENT=""
udevadm monitor --subsystem-match=usb --property | while IFS= read -r line; do
    if [ -z "$line" ]; then
        echo "$EVENT" | grep -q "ACTION=add" &&
        echo "$EVENT" | grep -q "ID_VENDOR_ID=$VENDOR" &&
        echo "$EVENT" | grep -q "ID_MODEL_ID=$PRODUCT" &&
        ratbagctl "$DEVICE_NAME" led 0 set mode off
        EVENT=""
    else
        EVENT=$(printf "%s\n" "$EVENT$line")
    fi
done
