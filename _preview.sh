#!/bin/sh

set -eu

BLUE_BOLD='\033[1;94m'
BOLD='\033[1m'
RESET='\033[0m'

if [ "${LF_LEVEL:-0}" -gt 0 ] && [ "$#" -eq 6 ] && [ "$6" = "preview" ]; then # most likely lf
    w="$2"
    h="$3"
else
    w="$(tput cols)"
    h="$(tput lines)"
fi

disp_img() {
    # threshold needed for lf to not have strip of prev image
    chafa --format sixel --scale max --view-size "$w"x"$h" --threshold 1 ${2:-} "$1"
}

[ -n "$1" ]
[ -e "$1" ] || (echo "Not Found: $1" && exit 1)

if [ -d "$1" ]; then
    LC_COLLATE=C ls --almost-all --color --format=commas --group-directories-first "$1" | tr ',' ' '
    exit 0
fi

mime_type=$(file --brief --mime-type --dereference "$1")
size=$( ( stat --format %s "$1" || stat -f %z "$1" ) | numfmt --to iec)

case "$mime_type" in
    inode/x-empty)
        ;;

    text/*)
        # glow won't color to pipe cuz of bug
        bat --terminal-width "$w" --color=always --style=plain "$1"
        ;;

    application/json)
        jq --color-output '.' "$1"
        ;;

    video/*)
        ffprobe -loglevel quiet -print_format json -show_format -show_streams -sexagesimal "$1" | \
        jq --raw-output '
            "HEAD|\(.format.format_long_name)|\(.format.duration)|\(.format.size)",
            (.streams[] | select(.codec_type == "video") |
                (.r_frame_rate | split("/") | map(tonumber) | .[0] / .[1]) as $fps |
                "VID|\(.index)|\(.width)x\(.height)|\($fps * 100 | round / 100)"),
            (.streams[] | select(.codec_type == "audio") |
                (.sample_rate | tonumber / 1000 | floor) as $khz |
                "AUD|\(.index)|\(.tags.language // "und")|\($khz)|\(.channel_layout)"),
            ( [.streams[] | select(.codec_type == "subtitle")] |
              if length > 0 then
                "SUB|\(length)|\(map(.tags.language // "und") | join(", "))"
              else empty end )
        ' | \
        while IFS="|" read -r type col1 col2 col3 col4; do
            case "$type" in
                HEAD)
                    dur=$(echo "$col2" | sed -e 's/^0://' -e 's/\..*$//')
                    size=$(numfmt --to iec -- "$col3")
                    size="$col3"
                    echo -e "${BLUE_BOLD}Video File$RESET"
                    printf "$BOLD%-10s$RESET %s\n" "Format:" "$col1"
                    printf "$BOLD%-10s$RESET %s\n" "Duration:" "$dur"
                    printf "$BOLD%-10s$RESET %s\n" "Size:" "$size"
                    ;;
                VID) printf "$BOLD%-10s$RESET %s @ %s fps\n" "Video:" "$col2" "$col3" ;;
                AUD) printf "$BOLD%-10s$RESET %s (%skHz %s)\n" "Audio:" "$col2" "$col3" "$col4" ;;
                SUB) printf "$BOLD%-10s$RESET %s\n" "Subs [$col1]:" "$col2" ;;
            esac
        done
        ;;

    image/*)
        disp_img "$1" # putting something above images causes weird bugs in fzf
        identify -ping -format '%m %G %B' "$1" | \
        awk -v c="$BLUE_BOLD" -v r="$RESET" '{
            "numfmt --to iec " $3 | getline hr
            printf "%s%s%s %s %s\n", c, $1, r, $2, hr
        }'
        ;;

    application/pdf)
        tmpfile=$(mktemp).jpg
        trap 'rm -f "$tmpfile"' EXIT
        pdftoppm -f 1 -l 1 -singlefile -scale-to-x 1920 -scale-to-y -1 -jpeg -- "$1" "${tmpfile%.jpg}"
        disp_img "$tmpfile"
        pdfinfo "$1" | awk -v c="$BLUE_BOLD" -v r="$RESET" '
            /^Pages:/ { pages = $2 }
            /^File size:/ { "numfmt --to iec " $3 | getline size }
            END { printf "%sPDF%s %s pages %s\n", c, r, pages, size }
        '
        ;;

    application/vnd.openxmlformats-officedocument.wordprocessingml.document)
        tmpdir=$(mktemp -d)
        trap 'rm -rf "$tmpdir"' EXIT
        loffice --headless --convert-to jpg --outdir "$tmpdir" "$1" >/dev/null
        disp_img "$tmpdir/$(basename "${1%.*}").jpg"
        pages=$(unzip -p "$1" docProps/app.xml | sed --quiet 's/.*<Pages>\([^<]*\)<\/Pages>.*/\1/p')
        echo -e "${BLUE_BOLD}DOCX$RESET $pages pages $size"
        ;;

    application/vnd.oasis.opendocument.text)
        tmpdir=$(mktemp -d)
        trap 'rm -rf "$tmpdir"' EXIT
        loffice --headless --convert-to jpg --outdir "$tmpdir" "$1" >/dev/null
        disp_img "$tmpdir/$(basename "${1%.*}").jpg"
        pages=$(unzip -p "$1" meta.xml | sed --quiet 's/.*meta:page-count="\([^"]*\)".*/\1/p')
        echo -e "${BLUE_BOLD}ODT$RESET $pages pages $size"
        ;;

    application/zip | application/x-zip* \
    | application/x-7z* \
    | application/vnd.rar | application/x-rar* \
    | application/x-tar \
    | application/gzip | application/x-gzip \
    | application/x-bzip* \
    | application/x-xz \
    | application/x-lz* | application/lz4 \
    | application/zstd \
    | application/x-brotli \
    | application/x-snappy*)
        type=$(file --brief --dereference "$1" | awk '{print toupper($1)}')
        echo -e "$BLUE_BOLD$type$RESET $size"
        ouch --yes list "$1" 2>/dev/null \
            | sed '1s/.*//' \
            | tree -C --fromfile \
            | awk '
                { lines[NR] = $0 }
                END {
                    print lines[NR]
                    for (i = 1; i < NR; i++) print lines[i]
                }
            '
        ;;

    *)
        file --brief --dereference "$1"
        echo -e "${BOLD}Mime Type:$RESET $mime_type"
        echo -e "${BOLD}Size:$RESET $size"
        ;;
esac
