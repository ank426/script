#!/bin/sh
[ -d "$HOME/.java" ] && EXISTED=true || EXISTED=false
java -jar "$XDG_DATA_HOME/mc4d/mc4d-4-3-343.jar"
[ -d "$HOME/.java" ] && [ "$EXISTED" = false ] && rm -rf "$HOME/.java" || true
