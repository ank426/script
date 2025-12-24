#!/bin/sh

bl=$(brightnessctl -e info | awk 'NR==2 {print int(substr(substr($NF, 1, length($NF)-2), 2)/5)*5}')

case $1 in
	get)
		echo $bl
		;;
	down)
		[ $bl -eq 0 ] || brightnessctl -e -q set $(($bl - 5))%
		;;
	up)
		[ $bl -eq 0 ] && brightnessctl -q set 1 || brightnessctl -e -q set $(($bl + 5))%
		;;
	*)
		echo 'Unknown argument'
		;;
esac
