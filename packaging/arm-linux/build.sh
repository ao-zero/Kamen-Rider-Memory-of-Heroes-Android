#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build & package Kamen Rider: Memory of Heroes (CUSA17374) into a strict nixport.port.v1 bundle:
#   kamen-rider-moh-port.zip
#   ├── port.json
#   ├── KamenRiderMoH-arm64.AppImage   (Type-2 AArch64 AppImage: runtime-aarch64 + SquashFS)
#   └── virtualkeys.json
#
# Environment flags:
#   KR_BUILD_RUNTIME=1   Compile native ARM64 shadPS4 + FEXCore via build-runtime.sh before packing
#   KR_STAGE_ONLY=1      Skip C++ runtime compilation (package launcher + 5,993-line Indo patch only)
#   KR_HOST_TOOLS=<dir>  Optional nixport repo checkout containing scripts/build-port-appimage.sh
set -euo pipefail

cd -- "$(dirname -- "$0")/../.."
root="$PWD"
pkg_dir="$root/packaging/arm-linux"
out_root="$root/out/arm64-linux"
appdir="$out_root/AppDir"
runtime_stage="$out_root/runtime-stage"
dist_dir="$pkg_dir/dist"

die() { echo "arm-linux/build: $*" >&2; exit 1; }

version=$(python3 -c "import json; print(json.load(open('$pkg_dir/port.json'))['version'])")
appimage_name=$(python3 -c "import json; print(json.load(open('$pkg_dir/port.json'))['appimage'])")

echo "=== Kamen Rider: Memory of Heroes ARM64 Port Builder (v$version) ==="

# ---- Step 1: Phase 4 Native ARM64 shadPS4 + FEXCore Runtime ------------------
if [[ "${KR_STAGE_ONLY:-0}" != "1" && "${KR_BUILD_RUNTIME:-0}" == "1" ]]; then
    echo ">> Building native ARM64 shadPS4 + FEXCore runtime..."
    KR_RUNTIME_STAGE="$runtime_stage" bash "$pkg_dir/build-runtime.sh"
elif [[ -x "$runtime_stage/bin/kr_core" ]]; then
    echo ">> Reusing pre-staged ARM64 runtime binary: $runtime_stage/bin/kr_core"
else
    echo ">> Runtime binary not staged (set KR_BUILD_RUNTIME=1 for full Phase 4 build). Packaging launcher + Patch Indo."
fi

# ---- Step 2: Assemble clean AppDir tree --------------------------------------
rm -rf "$appdir" "$dist_dir"
mkdir -p "$appdir/bin" "$appdir/lib" "$appdir/launcher" "$appdir/scripts" "$appdir/patches" "$appdir/assets" "$dist_dir"

cp "$pkg_dir/AppRun" "$appdir/AppRun"
cp "$pkg_dir/entry.sh" "$appdir/entry.sh"
cp "$pkg_dir/entry_main.py" "$appdir/entry_main.py"
chmod +x "$appdir/AppRun" "$appdir/entry.sh" "$appdir/entry_main.py"

cp "$root/launcher/kr_android_launcher.py" "$appdir/launcher/"
chmod +x "$appdir/launcher/kr_android_launcher.py"

cp "$root/scripts/"*.py "$appdir/scripts/"
cp "$root/patches/id_patch.json" "$appdir/patches/"
cp -R "$root/assets/." "$appdir/assets/"
cp "$root/LICENSE" "$appdir/LICENSE"
cp "$root/runtime/runtime-lock.json" "$appdir/runtime-lock.json"

# Standard AppImage metadata & icon inside AppDir (so nixport renders cover art cleanly)
if [[ -f "$root/assets/game_icon_rounded.png" ]]; then
    cp "$root/assets/game_icon_rounded.png" "$appdir/kamen-rider-moh.png"
    ln -sf kamen-rider-moh.png "$appdir/.DirIcon"
fi
cat > "$appdir/kamen-rider-moh.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Kamen Rider: Memory of Heroes
Exec=AppRun launcher
Icon=kamen-rider-moh
Categories=Game;
DESKTOP

# Copy compiled ARM64 runtime binary (and any extra non-rootfs libs) if present
if [[ -x "$runtime_stage/bin/kr_core" ]]; then
    install -m 755 "$runtime_stage/bin/kr_core" "$appdir/bin/kr_core"
    if [[ -d "$runtime_stage/lib" ]]; then
        cp -a "$runtime_stage/lib/." "$appdir/lib/"
    fi
fi

# ---- Step 3: AppRun verb smoke tests -----------------------------------------
echo ">> Running AppRun verb smoke tests (info / config schema / config get)..."
APPDIR="$appdir" KR_DATA_DIR="$out_root/smoke_home/kr_moh" "$appdir/AppRun" info | python3 -m json.tool >/dev/null
APPDIR="$appdir" KR_DATA_DIR="$out_root/smoke_home/kr_moh" "$appdir/AppRun" config schema | python3 -m json.tool >/dev/null
APPDIR="$appdir" KR_DATA_DIR="$out_root/smoke_home/kr_moh" "$appdir/AppRun" config get | python3 -m json.tool >/dev/null
rm -rf "$out_root/smoke_home"
echo ">> AppRun verb smoke tests PASSED."

# ---- Step 4: Pack Type-2 ARM64 AppImage --------------------------------------
appimage_path="$dist_dir/$appimage_name"
host_tools="${KR_HOST_TOOLS:-$root/fexdroid}"

if [[ -x "$host_tools/scripts/build-port-appimage.sh" ]]; then
    echo ">> Packing AppImage with nixport host script: $host_tools/scripts/build-port-appimage.sh"
    bash "$host_tools/scripts/build-port-appimage.sh" "$(cd "$appdir" && pwd)" "$appimage_path"
elif command -v mksquashfs >/dev/null 2>&1; then
    echo ">> Packing Type-2 AArch64 AppImage (AppImage/type2-runtime + SquashFS)..."
    rt_cache="$root/.local-deps/appimage-runtime-aarch64"
    mkdir -p "$root/.local-deps"
    if [[ ! -s "$rt_cache" ]]; then
        curl -fsSL --retry 3 --retry-delay 3 \
            -o "$rt_cache" \
            "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-aarch64" || true
    fi
    sqfs_tmp="$out_root/payload.squashfs"
    rm -f "$sqfs_tmp" "$appimage_path"
    mksquashfs "$appdir" "$sqfs_tmp" -root-owned -noappend -comp gzip -quiet
    if [[ -s "$rt_cache" ]]; then
        cat "$rt_cache" "$sqfs_tmp" > "$appimage_path"
    else
        echo ">> Warning: could not download type2 runtime-aarch64; falling back to raw SquashFS payload." >&2
        mv "$sqfs_tmp" "$appimage_path"
    fi
    rm -f "$sqfs_tmp"
    chmod +x "$appimage_path"
else
    die "Neither nixport build-port-appimage.sh nor mksquashfs is available."
fi

# ---- Step 5: Assemble strict nixport.port.v1 .zip (verified via Python) ------
# Strict nixport contract (verified from zFitness/gow3_android):
# Root of .zip MUST contain ONLY port.json, <AppImage>, and optional virtualkeys.json.
zip_out="$dist_dir/kamen-rider-moh-port.zip"
python3 - "$zip_out" "$pkg_dir/port.json" "$appimage_path" "$appimage_name" "$pkg_dir/virtualkeys.json" <<'PY'
import os
import sys
import zipfile

target, manifest, appimage_file, appimage_name, virtualkeys = sys.argv[1:6]
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
    zf.write(manifest, "port.json")
    zf.write(appimage_file, appimage_name)
    if os.path.isfile(virtualkeys):
        zf.write(virtualkeys, "virtualkeys.json")

with zipfile.ZipFile(target, "r") as zf:
    names = sorted(zf.namelist())
expected = sorted(["port.json", appimage_name, "virtualkeys.json"])
if names != expected:
    raise SystemExit(f"Strict nixport zip check failed: expected {expected}, got {names}")
print(f">> Verified strict nixport.port.v1 archive entries: {names}")
PY

echo "=== Build complete: $zip_out ==="
ls -lh "$zip_out"
