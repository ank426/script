#!/bin/sh

set -euo pipefail

# loffice is kinda bloat and does some weird cache shit and also needs to write to it
# so making it generate new cache every time would be too slow, but giving it write access would let it write malicious scripts, etc
LO_TEMP_DIR=$(mktemp -d)
trap "rm -rf '$LO_TEMP_DIR'" EXIT
if [ -d "$XDG_CONFIG_HOME/libreoffice" ] && ls -A "$XDG_CONFIG_HOME/libreoffice" >/dev/null 2>&1; then
    cp -r "$XDG_CONFIG_HOME/libreoffice/"* $LO_TEMP_DIR # it might be better to save a minimal profile for this
fi

(
    exec 10< "$XDG_DATA_HOME/../script/seccomp/bwrap-tiocsti.bpf"
    exec bwrap \
        --ro-bind / / \
        --tmpfs /tmp \
        --tmpfs "$HOME" \
        --bind "$LO_TEMP_DIR" "$XDG_CONFIG_HOME/libreoffice" \
        --ro-bind "$(realpath "$1")" "$(realpath "$1")" \
        --ro-bind "$XDG_DATA_HOME/../script/_preview.sh" "$XDG_DATA_HOME/../script/_preview.sh" \
        --proc /proc \
        --dev /dev \
        --unshare-all \
        --seccomp 10 \
        "$XDG_DATA_HOME/../script/_preview.sh" "$@"
)
