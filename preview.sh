#!/bin/bash

set -euo pipefail
(
    exec bwrap \
        --ro-bind / / \
        --tmpfs /tmp \
        --tmpfs "$HOME" \
        --ro-bind "$(realpath "$1")" "$(realpath "$1")" \
        --ro-bind "$XDG_DATA_HOME/../script/_preview.sh" "$XDG_DATA_HOME/../script/_preview.sh" \
        --proc /proc \
        --dev /dev \
        --unshare-all \
        --new-session \
        "$XDG_DATA_HOME/../script/_preview.sh" "$@"
)

# set -euo pipefail
# (
#     exec bwrap \
#      --ro-bind /usr/bin /usr/bin \
#      --ro-bind /usr/share/ /usr/share/ \
#      --ro-bind /usr/lib /usr/lib \
#      --ro-bind /usr/lib64 /usr/lib64 \
#      --symlink /usr/bin /bin \
#      --symlink /usr/bin /sbin \
#      --symlink /usr/lib /lib \
#      --symlink /usr/lib64 /lib64 \
#      --proc /proc \
#      --dev /dev  \
#      --tmpfs /tmp \
#      --ro-bind /etc /etc \
#      --ro-bind "$XDG_DATA_HOME/../script/_preview.sh" "$XDG_DATA_HOME/../script/_preview.sh"  \
#      --ro-bind "$PWD" "$PWD" \
#      --unshare-all \
#      --new-session \
#      "$XDG_DATA_HOME/../script/_preview.sh" "$@"
# )
#
#      # --ro-bind "$XDG_CONFIG_HOME" "$XDG_CONFIG_HOME" \
#      # --ro-bind "$XDG_CACHE_HOME" "$XDG_CACHE_HOME" \
