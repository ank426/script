#!/bin/sh

set -eu

if [ ! -e "$HOME/.cache" ]; then
    ln -s "$XDG_CACHE_HOME" "$HOME/.cache"
    trap 'rm "$HOME/.cache"' EXIT
fi

mokuro_flags=''
for arg in "$@"; do
    case "$arg" in -*) mokuro_flags="$mokuro_flags $arg" ;; esac
done

for path in "$@"; do
    case "$path" in -*) continue ;; esac

    attempts=0
    max_attempts=3
    case "$path" in
        *.cbz|*.zip) mokuro_file="${path%.*}.mokuro" ;;
        *)           mokuro_file="${path%/}.mokuro" ;;
    esac

    while [ "$attempts" -lt "$max_attempts" ]; do
        attempts=$((attempts + 1))
        if mokuro --disable_confirmation --legacy_html=False $mokuro_flags "$path"; then
            break
        fi
        printf 'mokuro failed on "%s" (attempt %d/%d)\n' "$path" "$attempts" "$max_attempts" >&2
        rm -f "$mokuro_file"
    done

    if [ "$attempts" -ge "$max_attempts" ]; then
        printf 'giving up on "%s" after %d attempts\n' "$path" "$max_attempts" >&2
        rm -f "$mokuro_file"
        continue
    fi
    jq '
      .pages |= [.[] | .blocks |= [
        .[] | select(.lines | any(test("\\p{Hiragana}|\\p{Katakana}|\\p{Han}")))
        | .vertical as $v
        | .lines |= [.[]
          | gsub("！！"; "‼")
          | gsub("！？"; "⁉")
          | gsub("？！"; "⁈")
          | gsub("？？"; "⁇")
          | gsub("．．．"; if $v then "︙" else "…" end)
          | gsub("．．"; if $v then "︰" else "‥" end)
        ]
      ]]
    ' "$mokuro_file" > "$mokuro_file.tmp" && mv "$mokuro_file.tmp" "$mokuro_file"
done
