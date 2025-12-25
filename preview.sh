#!/bin/sh

if [ "${LF_LEVEL:-0}" -gt 0 ] && [ "$#" -eq 6 ] && [ "$6" = "preview" ]; then # most likely lf
    img_size="$2x$3"
else
    img_size="$(tput cols)x$(tput lines)"
fi
disp_img() {
    chafa --format sixel --scale max --view-size $img_size --threshold 1 $2 "$1" # threshold needed for lf to not have strip of prev image
}


[ -z "$1" ] && exit 1
[ -d "$1" ] || [ -f "$1" ] || (echo "Not Found: $1" && exit 1)

if [ -d "$1" ]; then
    LC_COLLATE=C ls --almost-all --color --format=commas --group-directories-first "$1" | tr ',' ' '
    exit 0
fi

mime_type=$(file --brief --mime-type --dereference "$1" 2>/dev/null || exit 1)
size=$(stat --format %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || exit 1)

case "$mime_type" in
    inode/x-empty)
        ;;

    text/*)
        bat --color=always --style=plain "$1"
        ;;

    video/*)
        echo -e "\033[1;94m$mime_type\033[0m"
        ffprobe -loglevel quiet -show_format "$1" | tail -n +2 | sed '$d'
        ;;

    image/*)
        disp_img "$1" # putting something above images causes weird bugs in fzf
        identify -ping -format '%m %G %B' "$1" |
            awk '{
            cmd = "numfmt --to iec " $3
            cmd | getline hr
            close(cmd)
            printf "\033[94m%s\033[0m %s %s\n", $1, $2, hr
        }'
        ;;

    application/pdf)
        tmpfile=$(mktemp)
        pdftoppm -f 1 -l 1 -singlefile -scale-to-x 1920 -scale-to-y -1 -jpeg -- "$1" "$tmpfile"
        disp_img "$tmpfile.jpg"
        pdfinfo "$1" | awk '
            /^Pages:/ { pages = $2 }
            /^File size:/ {
                cmd = "numfmt --to iec " $3
                cmd | getline size
                close(cmd)
            }
            END {
                printf "\033[94mPDF\033[0m %s pages %s\n", pages, size
            }
        '
        rm "$tmpfile.jpg"
        ;;

    application/vnd.openxmlformats-officedocument.wordprocessingml.document)
        tmpdir=$(mktemp -d)
        loffice --headless --convert-to jpg --outdir "$tmpdir" "$1" >/dev/null
        disp_img "$tmpdir/$(basename "${1%.*}").jpg"
        echo -e "\033[94mDOCX\033[0m $(unzip -p "$1" docProps/app.xml | grep -oP '(?<=<Pages>)[^<]+') pages $(numfmt --to iec $size)\n"
        rm -rf "$tmpdir"
        ;;

    application/vnd.oasis.opendocument.text)
        tmpdir=$(mktemp -d)
        loffice --headless --convert-to jpg --outdir "$tmpdir" "$1" >/dev/null
        disp_img "$tmpdir/$(basename "${1%.*}").jpg"
        echo -e "\033[94mODT\033[0m $(unzip -p "$1" meta.xml | grep -oP 'meta:page-count="\K[^"]+') pages $(numfmt --to iec $size)\n"
        rm -rf "$tmpdir"
        ;;

    application/zip | application/x-zip*)
        echo -e "\033[1;94m$mime_type\033[0m"
        unzip -l "$1" | tail -n +2
        ;;

    application/x-tar | application/x-gzip | application/x-bzip2)
        echo -e "\033[1;94m$mime_type\033[0m"
        tar tf "$1"
        ;;

    *)
        echo -e "\033[1;94mBinary File\033[0m"
        echo "Type: $mime_type"
        echo "Size: $size bytes"
        ;;
esac
