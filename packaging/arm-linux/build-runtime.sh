#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Phase 4: Cross-compile native ARM64 shadPS4 + FEXCore guest CPU backend (bin/kr_core)
# Configured specifically for nixport (Debian Trixie ARM64):
#   1. ENABLE_FEX_GUEST_CPU=ON (x86-64 PS4 guest code -> ARM64 JIT)
#   2. ENABLE_BACHATA_RUNTIME=OFF (enables standard SDLAudioOut -> PulseAudio & SDL_INIT_GAMEPAD)
#   3. SDL_SHARED=ON (builds dynamic libSDL3.so.0 required by nixport's libfexpad.so virtual gamepad shim)
set -euo pipefail

cd -- "$(dirname -- "$0")/../.."
root="$PWD"
lock_file="$root/runtime/runtime-lock.json"
src_dir="${KR_RUNTIME_SRC:-$root/.local-deps/shadps4-arm64}"
stage_out="${KR_RUNTIME_STAGE:-$root/out/arm64-linux/runtime-stage}"

die() { echo "build-runtime: $*" >&2; exit 1; }

repo_url="${KR_RUNTIME_REPO:-$(python3 -c "import json; print(json.load(open('$lock_file'))['repository'])")}"
repo_ref="${KR_RUNTIME_REF:-$(python3 -c "import json; print(json.load(open('$lock_file'))['commit'])")}"
builder_image="${KR_BUILDER_IMAGE:-$(python3 -c "import json; print(json.load(open('$lock_file'))['builder_image'])")}"

echo "=== Phase 4 Runtime Builder: shadPS4 ARM64 + FEXCore + Dynamic SDL3 (nixport) ==="
echo "  Repository : $repo_url"
echo "  Pinned Ref : $repo_ref"
echo "  Source Dir : $src_dir"
echo "  Stage Out  : $stage_out"

# ---- Step 1: Checkout clean pinned shadps4-arm64 + submodules ----------------
if [[ ! -d "$src_dir/.git" ]]; then
    mkdir -p "$(dirname "$src_dir")"
    git clone --filter=blob:none "$repo_url" "$src_dir"
fi
git -C "$src_dir" fetch --depth 1 origin "$repo_ref" || git -C "$src_dir" fetch origin
git -C "$src_dir" reset --hard
git -C "$src_dir" checkout --force "$repo_ref"
git -C "$src_dir" submodule sync --recursive
git -C "$src_dir" submodule foreach --recursive git reset --hard || true
git -C "$src_dir" submodule update --init --recursive --depth 1 --jobs 8

# ---- Step 2: Patch source tree for nixport (SDLAudioOut + SDL_INIT_GAMEPAD + libSDL3.so.0) ----
python3 - "$src_dir" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])

# 1) Guard bachata_audio_out.cpp so ENABLE_BACHATA_RUNTIME=OFF links cleanly
cm = src / "CMakeLists.txt"
cm_txt = cm.read_text(encoding="utf-8")
target_audio = "              src/core/libraries/audio/bachata_audio_out.cpp\n"
if target_audio in cm_txt:
    cm_txt = cm_txt.replace(target_audio, "")
    cm_txt = cm_txt.replace(
        "if (ENABLE_BACHATA_RUNTIME)\n    target_compile_definitions(shadps4 PRIVATE ENABLE_BACHATA_RUNTIME)\n    target_sources(shadps4 PRIVATE\n",
        "if (ENABLE_BACHATA_RUNTIME)\n    target_compile_definitions(shadps4 PRIVATE ENABLE_BACHATA_RUNTIME)\n    target_sources(shadps4 PRIVATE\n        src/core/libraries/audio/bachata_audio_out.cpp\n",
    )
    cm.write_text(cm_txt, encoding="utf-8")
    print("[patch] Guarded bachata_audio_out.cpp behind ENABLE_BACHATA_RUNTIME")

# 2) Build bundled SDL3 as a SHARED library (libSDL3.so.0) with dynamic PulseAudio enabled
ext_cm = src / "externals" / "CMakeLists.txt"
ext_txt = ext_cm.read_text(encoding="utf-8")
sdl_orig = """# SDL3
if (NOT TARGET SDL3::SDL3)
    set(SDL_TEST_LIBRARY OFF)
    set(SDL_PIPEWIRE OFF)
    set(SDL_AVX512F OFF)
    add_subdirectory(sdl3)
endif()"""
sdl_new = """# SDL3 (Dynamic shared library required by nixport libfexpad.so virtual gamepad shim)
if (NOT TARGET SDL3::SDL3)
    set(SDL_TEST_LIBRARY OFF)
    set(SDL_PIPEWIRE OFF)
    set(SDL_AVX512F OFF)
    set(SDL_SHARED ON CACHE BOOL "" FORCE)
    set(SDL_STATIC OFF CACHE BOOL "" FORCE)
    set(SDL_PULSEAUDIO ON CACHE BOOL "" FORCE)
    set(SDL_PULSEAUDIO_SHARED ON CACHE BOOL "" FORCE)
    set(SDL_ALSA ON CACHE BOOL "" FORCE)
    set(SDL_ALSA_SHARED ON CACHE BOOL "" FORCE)
    add_subdirectory(sdl3)
endif()"""
assert sdl_orig in ext_txt, "Expected SDL3 block not found in externals/CMakeLists.txt"
ext_cm.write_text(ext_txt.replace(sdl_orig, sdl_new, 1), encoding="utf-8")
print("[patch] Configured externals/sdl3 as shared libSDL3.so.0 + PulseAudio")

# 3) Keep Android X11/VM safety guards in sdl_window.cpp & emulator.cpp when ENABLE_BACHATA_RUNTIME=OFF
sw = src / "src" / "sdl_window.cpp"
sw_txt = sw.read_text(encoding="utf-8")
assert "#ifdef ENABLE_BACHATA_RUNTIME\n    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_X_NUMBER, 0);" in sw_txt
sw_txt = sw_txt.replace(
    "#ifdef ENABLE_BACHATA_RUNTIME\n    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_X_NUMBER, 0);",
    "#if defined(ENABLE_BACHATA_RUNTIME) || defined(__aarch64__)\n    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_X_NUMBER, 0);",
    1,
)
assert "void WindowSDL::SetIcon(const std::filesystem::path& path) {\n#ifdef ENABLE_BACHATA_RUNTIME" in sw_txt
sw_txt = sw_txt.replace(
    "void WindowSDL::SetIcon(const std::filesystem::path& path) {\n#ifdef ENABLE_BACHATA_RUNTIME",
    "void WindowSDL::SetIcon(const std::filesystem::path& path) {\n#if defined(ENABLE_BACHATA_RUNTIME) || defined(__aarch64__)",
    1,
)
sw.write_text(sw_txt, encoding="utf-8")
print("[patch] Preserved X11 (0,0) origin and SetIcon WSI guard on __aarch64__ in sdl_window.cpp")

em = src / "src" / "emulator.cpp"
em_txt = em.read_text(encoding="utf-8")
orig_em_early = """#ifndef ENABLE_BACHATA_RUNTIME
    memory = Core::Memory::Instance();
#endif
    controllers = Common::Singleton<Input::GameControllers>::Instance();
#ifndef ENABLE_BACHATA_RUNTIME
    linker = Common::Singleton<Core::Linker>::Instance();
#endif"""
new_em_early = """#if !defined(ENABLE_BACHATA_RUNTIME) && !defined(__aarch64__)
    memory = Core::Memory::Instance();
#endif
    controllers = Common::Singleton<Input::GameControllers>::Instance();
#if !defined(ENABLE_BACHATA_RUNTIME) && !defined(__aarch64__)
    linker = Common::Singleton<Core::Linker>::Instance();
#endif"""
orig_em_late = """#ifdef ENABLE_BACHATA_RUNTIME
    memory = Core::Memory::Instance();
    linker = Common::Singleton<Core::Linker>::Instance();
#endif"""
new_em_late = """#if defined(ENABLE_BACHATA_RUNTIME) || defined(__aarch64__)
    memory = Core::Memory::Instance();
    linker = Common::Singleton<Core::Linker>::Instance();
#endif"""
assert orig_em_early in em_txt and orig_em_late in em_txt, "Expected memory/linker init guards not found in emulator.cpp"
em_txt = em_txt.replace(orig_em_early, new_em_early, 1).replace(orig_em_late, new_em_late, 1)
em.write_text(em_txt, encoding="utf-8")
print("[patch] Deferred Core::Memory & Core::Linker init until after WindowSDL on __aarch64__")

# 4) Switch build-shadps4-arm64.sh to ENABLE_BACHATA_RUNTIME=OFF and add $ORIGIN/../lib rpath
bs = src / "runtime" / "scripts" / "build-shadps4-arm64.sh"
bs_txt = bs.read_text(encoding="utf-8")
assert "-DENABLE_BACHATA_RUNTIME=ON" in bs_txt, "ENABLE_BACHATA_RUNTIME=ON not found in build-shadps4-arm64.sh"
bs_txt = bs_txt.replace("-DENABLE_BACHATA_RUNTIME=ON", "-DENABLE_BACHATA_RUNTIME=OFF")
bs_txt = bs_txt.replace(
    '-DCMAKE_EXE_LINKER_FLAGS:STRING="-L$arm64_link_dir -Wl,--build-id=sha1"',
    '-DCMAKE_EXE_LINKER_FLAGS:STRING="-L$arm64_link_dir -Wl,--build-id=sha1 -Wl,-rpath,\\$ORIGIN/../lib"',
)
bs.write_text(bs_txt, encoding="utf-8")
print("[patch] Switched build-shadps4-arm64.sh to ENABLE_BACHATA_RUNTIME=OFF + rpath")
PY

# ---- Step 3: Run Debian Trixie ARM64 cross-compile ---------------------------
inner_cmd='
    bash runtime/scripts/install-debian-runtime-deps.sh
    apt-get install --yes --no-install-recommends -o Acquire::Retries=3 \
        libpulse-dev:arm64 libpulse0:arm64 libasound2-dev:arm64 libasound2t64:arm64 || \
    apt-get install --yes --no-install-recommends -o Acquire::Retries=3 \
        libpulse-dev:arm64 libasound2-dev:arm64
    export PKG_CONFIG_PATH=""
    export PKG_CONFIG_LIBDIR="/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/share/pkgconfig"
    git config --global --add safe.directory "*"
    bash runtime/scripts/build-shadps4-arm64.sh
    grep -E "SDL_AUDIO_DRIVER_" runtime/build/shadps4-arm64/externals/sdl3/include-config-release/build_config/SDL_build_config.h || true
'

is_debian_trixie=0
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    if [[ "${ID:-}" == "debian" && "${VERSION_CODENAME:-}" == "trixie" ]]; then
        is_debian_trixie=1
    fi
fi

if [[ "$is_debian_trixie" == "1" ]]; then
    echo ">> Running natively inside Debian Trixie..."
    bash -euo pipefail -c "$inner_cmd"
elif command -v docker >/dev/null 2>&1; then
    echo ">> Launching reproducible $builder_image Docker container for ARM64 cross-build..."
    docker run --rm \
        -e BACHATA_INSIDE_DEBIAN_CONTAINER=1 \
        -e DEBIAN_FRONTEND=noninteractive \
        -v "$src_dir:/workspace" \
        -w /workspace \
        "$builder_image" \
        bash -euo pipefail -c "$inner_cmd"
else
    die "Building shadps4-arm64 requires Debian Trixie or Docker (available on GitHub Actions ubuntu-24.04)."
fi

# ---- Step 4: Stage verified AArch64 ELF binary + libSDL3.so.0 ----------------
built_bin="$src_dir/runtime/build/shadps4-arm64-stage/bin/shadps4-arm64"
needed_txt="$src_dir/runtime/build/shadps4-arm64-stage/needed.txt"
sdl_build_dir="$src_dir/runtime/build/shadps4-arm64/externals/sdl3"
[[ -f "$built_bin" ]] || die "Expected built binary not found: $built_bin"

if command -v readelf >/dev/null 2>&1; then
    hdr=$(readelf -h "$built_bin")
    grep -Eq 'Class:[[:space:]]+ELF64' <<<"$hdr" || die "Built binary is not ELF64"
    grep -Eq 'Machine:[[:space:]]+AArch64' <<<"$hdr" || die "Built binary is not AArch64"
    readelf -d "$built_bin" | grep -Fq 'libSDL3.so.0' || die "Built binary did not dynamically link libSDL3.so.0"
fi

rm -rf "$stage_out"
mkdir -p "$stage_out/bin" "$stage_out/lib"
install -m 755 "$built_bin" "$stage_out/bin/kr_core"

# Copy built ARM64 libSDL3.so.0* (preserving symlinks) into stage_out/lib
found_sdl=0
for cand in "$sdl_build_dir"/libSDL3.so*; do
    if [[ -e "$cand" || -L "$cand" ]]; then
        cp -P "$cand" "$stage_out/lib/"
        found_sdl=1
    fi
done
[[ "$found_sdl" == "1" ]] || die "libSDL3.so.0 was not found under $sdl_build_dir"

if [[ -f "$needed_txt" ]]; then
    cp "$needed_txt" "$stage_out/needed.txt"
    echo "=== Dynamic NEEDED libraries of kr_core ==="
    cat "$stage_out/needed.txt"
fi

echo "=== Phase 4 Runtime Ready: $stage_out/bin/kr_core + libSDL3.so.0 ==="
ls -lh "$stage_out/bin/kr_core" "$stage_out/lib/"
