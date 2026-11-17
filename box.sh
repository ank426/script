#!/bin/sh
# box.sh: run any command with dotfile redirects into XDG dirs.
# Usage: box.sh <command> [args...]

set -eu

[ "$#" -gt 0 ] || { echo "usage: ${0##*/} <command> [args...]" >&2; exit 1; }

# <path under $HOME>  <real location>   (no spaces in paths)
redirects() {
  cat <<EOF
.config $XDG_CONFIG_HOME
.cache $XDG_CACHE_HOME
.local $XDG_DATA_HOME/..
.pki $XDG_DATA_HOME/pki
.epy $XDG_CONFIG_HOME/epy
EOF
}

n=$#
set -- "$@" --dev-bind / / --tmpfs "$HOME"

# Pass everything in $HOME through...
for f in "$HOME"/* "$HOME"/.[!.]*; do
  [ -e "$f" ] && set -- "$@" --bind "$f" "$f"
done

# ...then layer the redirects over it
while read -r rel src; do
  mkdir -p "$src"
  set -- "$@" --bind "$src" "$HOME/$rel"
done <<EOF
$(redirects)
EOF

# Move the original command from the front back to the end
while [ "$n" -gt 0 ]; do
  set -- "$@" "$1"
  shift
  n=$((n - 1))
done

exec bwrap "$@"
