#!/bin/sh

set -eu

if [ $# -ne 2 ]; then
    echo "Usage: kiru.sh <input_dir> <output_dir>" >&2
    exit 1
fi

input_dir="$1"
output_dir="$2"

if [ ! -d "$input_dir" ]; then
    echo "Error: input directory does not exist: $input_dir" >&2
    exit 1
fi

mkdir -p "$output_dir"

if [ "$(realpath "$input_dir")" = "$(realpath "$output_dir")" ]; then
    echo "Error: output dir must differ from input dir" >&2
    exit 1
fi

filelist=$(mktemp)
trap "rm -f $filelist" EXIT

for f in "$input_dir"/*; do
    [ -f "$f" ] || continue
    case "$f" in
        *.[jJ][pP][gG]|*.[jJ][pP][eE][gG]|*.[pP][nN][gG]|*.[wW][eE][bB][pP])
            printf '%s\n' "$f"
            ;;
    esac
done | sort -V > "$filelist"

count=$(wc -l < "$filelist")
if [ "$count" -eq 0 ]; then
    echo "Warning: no image files found in $input_dir" >&2
    exit 1
fi

idx=0
while IFS= read -r file; do
    dims=$(magick identify -format '%w %h' "$file")
    w=${dims%% *}
    h=${dims##* }
    if [ "$w" -gt "$h" ]; then
        half_w=$((w / 2))
        idx=$((idx + 1))
        magick "$file" -crop "${half_w}x$h+${half_w}+0" +repage "$output_dir/$idx.png"
        idx=$((idx + 1))
        magick "$file" -crop "${half_w}x$h+0+0" +repage "$output_dir/$idx.png"
    else
        idx=$((idx + 1))
        magick "$file" "$output_dir/$idx.png"
    fi
done < "$filelist"

echo "Processed $count files → $idx output files" >&2
