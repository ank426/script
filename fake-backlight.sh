#!/bin/sh

state_path=/tmp/fake-backlight
[ -f $state_path ] && fbl=$(cat $state_path) || fbl=100

case $1 in
	get)
		echo $fbl
		;;
	g)
		[ $fbl -eq 100 ] || echo $((($fbl + 5) / 10))
		;;
	set)
		pgrep -x gammastep > /dev/null && killall gammastep
		fbl=$(($fbl + $2))
		if [ $fbl -ge 100 ]; then
			[ ! -f $state_path ] || rm $state_path
		else
			[ $fbl -lt 10 ] && fbl=10
			# idk why both -o and & are needed but they are
			# also -P doesn't seem to work
			gammastep -o -b "0.$fbl" &
			echo $fbl > $state_path
		fi
		;;
	*)
		echo 'Unknown argument'
		;;
esac
