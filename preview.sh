#!/bin/sh

set -eu

XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
script_dir="$XDG_DATA_HOME/../script"

# loffice is kinda bloat and does some weird cache shit and also needs to write to it
# so making it generate new cache every time would be too slow, but giving it write access would let it write malicious scripts, etc
LO_TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$LO_TEMP_DIR"' EXIT

if [ -d "$XDG_CONFIG_HOME/libreoffice" ] && [ -n "$(ls -A "$XDG_CONFIG_HOME/libreoffice" 2>/dev/null)" ]; then
    cp -R "$XDG_CONFIG_HOME/libreoffice/"* "$LO_TEMP_DIR" # it might be better to save a minimal profile for this
fi

# realpath isn't POSIX: resolve the directory with pwd -P instead
resolved=$(cd "$(dirname "$1")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$1")")
shift

(
    exec 9< "$script_dir/seccomp/bwrap-tiocsti.bpf"
    exec bwrap \
        --ro-bind / / \
        --tmpfs /tmp \
        --tmpfs "$HOME" \
        --bind "$LO_TEMP_DIR" "$XDG_CONFIG_HOME/libreoffice" \
        --ro-bind "$resolved" "$resolved" \
        --ro-bind "$script_dir/_preview.sh" "$script_dir/_preview.sh" \
        --proc /proc \
        --dev /dev \
        --unshare-all \
        --seccomp 9 \
        "$script_dir/_preview.sh" "$resolved" "$@"
)
