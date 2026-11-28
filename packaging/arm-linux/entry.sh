#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Kamen Rider: Memory of Heroes (CUSA17374) | nixport Runtime Verb Contract
# Supported verbs: launcher | game | info | config | check | vulkan
# Rule: stdout MUST be pure JSON for `config` and `info`; diagnostics go to stderr.
set -eu

# Save host LD_PRELOAD (e.g. libfexpad.so) and clear it for shell/Python helper processes
# so fexpad does not stall dash/mkdir/python3.13 waiting 30s for SDL3.
if [ -n "${LD_PRELOAD:-}" ] && [ -z "${KR_SAVED_LD_PRELOAD:-}" ]; then
    export KR_SAVED_LD_PRELOAD="$LD_PRELOAD"
fi
unset LD_PRELOAD

TREE="${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
PKG="$(dirname "$TREE")"
if [ -n "${FEXDROID_PRESENT:-}" ] || [ -d "$PKG/home" ]; then
    DATA="${KR_DATA_DIR:-$PKG/home/kr_moh}"
else
    DATA="${KR_DATA_DIR:-${HOME:-$PKG/home}/kr_moh}"
fi
CONFIG="${KR_CONFIG:-$DATA/launcher.ini}"
HOST="${FXD_ROOT:-/data/user/0/ro.cobrabm.fexdroid/files/rootfs}"
LOADER="$HOST/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"

PY_BIN="python3.13"
command -v "$PY_BIN" >/dev/null 2>&1 || PY_BIN="python3"

run_py() {
    if [ -x "$LOADER" ] && [ -x "$HOST/usr/bin/python3.13" ]; then
        LD_LIBRARY_PATH="$HOST/usr/lib/aarch64-linux-gnu:$HOST/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
            "$LOADER" "$HOST/usr/bin/python3.13" "$@"
    else
        "$PY_BIN" "$@"
    fi
}

exec_py() {
    if [ -x "$LOADER" ] && [ -x "$HOST/usr/bin/python3.13" ]; then
        LD_LIBRARY_PATH="$HOST/usr/lib/aarch64-linux-gnu:$HOST/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
            exec "$LOADER" "$HOST/usr/bin/python3.13" "$@"
    else
        exec "$PY_BIN" "$@"
    fi
}

exec_arm64_bin() {
    BIN_PATH="$1"
    shift
    LIB_PATH="$TREE/lib:$HOST/usr/lib/aarch64-linux-gnu:$HOST/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    PAD_PRELOAD="${KR_SAVED_LD_PRELOAD:-}"
    if [ -z "$PAD_PRELOAD" ] && [ -f "$HOST/usr/lib/fexdroid/libfexpad.so" ]; then
        PAD_PRELOAD="$HOST/usr/lib/fexdroid/libfexpad.so"
    fi
    if [ -n "$PAD_PRELOAD" ]; then
        export LD_PRELOAD="$PAD_PRELOAD"
    fi
    if [ ! -e "/lib/ld-linux-aarch64.so.1" ] && [ -x "$LOADER" ]; then
        LD_LIBRARY_PATH="$LIB_PATH" exec "$LOADER" --library-path "$LIB_PATH" "$BIN_PATH" "$@"
    fi
    export LD_LIBRARY_PATH="$LIB_PATH"
    exec "$BIN_PATH" "$@"
}

setup_env() {
    mkdir -p "$DATA/logs" "$DATA/saves_backup" "$DATA/bin/user/log" "$DATA/bin/user/input_config" "$DATA/bin/user/vanilla_backup"
    export KR_APP_DIR="$TREE"
    export KR_DATA_DIR="$DATA"
    export KR_CONFIG="$CONFIG"
    if [ -n "${FEXDROID_PRESENT:-}" ]; then
        export KR_DEVICE_UI="${KR_DEVICE_UI:-1}"
    fi
    export XDG_DATA_HOME="$DATA/bin/user"

    # Point Tcl/Tk and XKB to nixport's rootfs (non-root Android has no /usr)
    if [ -z "${TCL_LIBRARY:-}" ]; then
        for cand in "$HOST/usr/share/tcltk/tcl8.6" "$HOST/usr/lib/tcl8.6"; do
            if [ -d "$cand" ]; then
                export TCL_LIBRARY="$cand"
                break
            fi
        done
    fi
    if [ -z "${TK_LIBRARY:-}" ]; then
        for cand in "$HOST/usr/share/tcltk/tk8.6" "$HOST/usr/lib/tk8.6"; do
            if [ -d "$cand" ]; then
                export TK_LIBRARY="$cand"
                break
            fi
        done
    fi
    if [ -z "${XKB_CONFIG_ROOT:-}" ] && [ -d "$HOST/usr/share/X11/xkb" ]; then
        export XKB_CONFIG_ROOT="$HOST/usr/share/X11/xkb"
    fi
    if [ -z "${FONTCONFIG_PATH:-}" ] && [ -d "$HOST/etc/fonts" ]; then
        export FONTCONFIG_PATH="$HOST/etc/fonts"
    fi
    if [ -d "$TREE/lib" ]; then
        export LD_LIBRARY_PATH="$TREE/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
}

VERB="${1:-launcher}"
if [ $# -gt 0 ]; then
    shift
fi

setup_env

case "$VERB" in
    launcher)
        {
            echo "=== launcher $(date) DISPLAY=${DISPLAY:-unset} TCL_LIBRARY=${TCL_LIBRARY:-unset} TK_LIBRARY=${TK_LIBRARY:-unset} ==="
        } >> "$DATA/logs/launch.log" 2>&1 || true
        exec_py "$TREE/launcher/kr_android_launcher.py" "$@" 2>> "$DATA/logs/launch.log"
        ;;

    game)
        run_py "$TREE/entry_main.py" sync "$CONFIG" >&2
        GAME_DIR="$(run_py "$TREE/entry_main.py" get-game-dir "$CONFIG")"
        if [ -z "$GAME_DIR" ] || [ ! -f "$GAME_DIR/eboot.bin" ]; then
            echo "[kr-moh] ERROR: CUSA17374 eboot.bin not found (game_dir='$GAME_DIR'). Open Launcher to configure." >&2
            exit 2
        fi
        CORE_BIN=""
        for cand in "$TREE/bin/kr_core" "$TREE/bin/shadps4" "$DATA/bin/kr_core" "$DATA/bin/shadps4"; do
            if [ -x "$cand" ]; then
                CORE_BIN="$cand"
                break
            fi
        done
        if [ -z "$CORE_BIN" ]; then
            echo "[kr-moh] ERROR: ARM64 runtime binary (bin/kr_core) is not bundled yet." >&2
            exit 3
        fi
        LOG_FILE="$DATA/logs/launch.log"
        SHOW_FPS="$(run_py "$TREE/entry_main.py" get-key show_fps "$CONFIG" || echo true)"
        VID_DRV="$(run_py "$TREE/entry_main.py" get-key video_backend "$CONFIG" || echo auto)"
        if [ -n "$VID_DRV" ] && [ "$VID_DRV" != "auto" ]; then
            export SDL_VIDEODRIVER="$VID_DRV"
        fi
        # Run from $DATA/bin so shadPS4 detects portable ./user/ (config.json, input_config, savedata)
        cd "$DATA/bin"
        echo "[kr-moh] Launching $CORE_BIN -g $GAME_DIR/eboot.bin (cwd=$DATA/bin)" >&2
        if [ "$SHOW_FPS" = "true" ]; then
            exec_arm64_bin "$CORE_BIN" -g "$GAME_DIR/eboot.bin" -f true --show-fps "$@" >"$LOG_FILE" 2>&1
        else
            exec_arm64_bin "$CORE_BIN" -g "$GAME_DIR/eboot.bin" -f true "$@" >"$LOG_FILE" 2>&1
        fi
        ;;

    info)
        exec_py "$TREE/entry_main.py" info "${1:-summary}" "$CONFIG"
        ;;

    config)
        SUB="${1:-get}"
        if [ $# -gt 0 ]; then
            shift
        fi
        if [ "$SUB" = "set" ]; then
            PAYLOAD="${1:-{}}"
            exec_py "$TREE/entry_main.py" config set "$PAYLOAD" "$CONFIG"
        else
            exec_py "$TREE/entry_main.py" config "$SUB" "$CONFIG"
        fi
        ;;

    check|vulkan)
        exec_py "$TREE/entry_main.py" check "$CONFIG"
        ;;

    *)
        echo "[kr-moh] Unknown verb: $VERB (expected: launcher|game|info|config|check|vulkan)" >&2
        exit 64
        ;;
esac
