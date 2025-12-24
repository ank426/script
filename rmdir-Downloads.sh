while true; do
	[ -d ~/Downloads ] && [ -z "$(ls -A ~/Downloads)" ] && rmdir ~/Downloads
	sleep 1
done
