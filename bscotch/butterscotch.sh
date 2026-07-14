#!/bin/bash

set -x
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LOGFILE="$STEAM_COMPAT_INSTALL_PATH/butterscotch.log"
exec >> "$LOGFILE" 2>&1

if [[ $2 == *"iscriptevaluator.exe"* ]]; then
  echo "ignoring iscriptevaluator.exe"
  exit 0
fi

if [ -z "$SteamAppId" ]; then
  echo "bscotch - Exiting because no steam app id"
  exit 0
fi

DATA_WIN="$STEAM_COMPAT_INSTALL_PATH/data.win"

if [ -f "$DATA_WIN" ]; then
    echo "Using default path!"
else
    echo "Using auto-detect."
    DATA_WIN="$(find "$STEAM_COMPAT_INSTALL_PATH" -type f -iname "data.win" | head -n1)"
fi

if [ -z "$DATA_WIN" ]; then
    echo "Could not find data.win inside $STEAM_COMPAT_INSTALL_PATH"
    exit 1
fi

echo "Using data.win: $DATA_WIN"

python3 "$DIR/resolve_savepath.py" \
    --appid "${SteamAppId:-0}" \
    --client "$STEAM_COMPAT_CLIENT_INSTALL_PATH" \
    --install "$STEAM_COMPAT_INSTALL_PATH" \
    > /tmp/bscotch_savepath.out 2> /tmp/bscotch_savepath.err
RESOLVED=$(cat /tmp/bscotch_savepath.out)
if [ -n "$RESOLVED" ] && [ -d "$RESOLVED" ]; then
    GAME_SAVE_DIR="$RESOLVED"
    echo "Save path resolvido (UFS/appinfo.vdf): $GAME_SAVE_DIR"
else
    echo "WARN: resolve_savepath falhou; stderr:" >&2
    cat /tmp/bscotch_savepath.err >&2
    GAME_SAVE_DIR="$STEAM_COMPAT_INSTALL_PATH/bscotch-savedata/"
    echo "Save path (fallback install): $GAME_SAVE_DIR"
fi

cd "$DIR/build"
"$DIR/build/butterscotch" --lazy-texture \
     --save-folder "$GAME_SAVE_DIR" \
     "$DATA_WIN"
exit $?