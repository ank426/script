#!/bin/sh

uid=$(id -u)
state_path="/tmp/fake-backlight-$uid"

if [ -f "$state_path" ]; then
	fbl=$(cat "$state_path")
else
	fbl=100
fi

case $1 in
	get)
		echo "$fbl"
		;;
	g)
		[ "$fbl" -eq 100 ] || echo $(( (fbl + 5) / 10 ))
		;;
	set)
		pgrep -u "$uid" -x gammastep > /dev/null && pkill -u "$uid" -x gammastep
		fbl=$(( fbl + $2 ))
		if [ "$fbl" -ge 100 ]; then
			[ ! -f "$state_path" ] || rm "$state_path"
		else
			[ "$fbl" -lt 10 ] && fbl=10
			# idk why both -o and & are needed but they are
			# also -P doesn't seem to work
			gammastep -o -b "0.$fbl" &
			echo "$fbl" > "$state_path"
		fi
		;;
	*)
		echo 'Unknown argument'
		;;
esac
