#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Phase 4: Cross-compile native ARM64 shadPS4 + FEXCore guest CPU backend (bin/kr_core)
# Uses a reproducible Debian Trixie (amd64 host -> arm64 target) environment matching
# nixport's Debian 13 ARM64 glibc ABI.
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

echo "=== Phase 4 Runtime Builder: shadPS4 ARM64 + FEXCore ==="
echo "  Repository : $repo_url"
echo "  Pinned Ref : $repo_ref"
echo "  Source Dir : $src_dir"
echo "  Stage Out  : $stage_out"

# ---- Step 1: Checkout pinned shadps4-arm64 + submodules ----------------------
if [[ ! -d "$src_dir/.git" ]]; then
    mkdir -p "$(dirname "$src_dir")"
    git clone --filter=blob:none "$repo_url" "$src_dir"
fi
git -C "$src_dir" fetch --depth 1 origin "$repo_ref" || git -C "$src_dir" fetch origin
git -C "$src_dir" checkout --force "$repo_ref"
git -C "$src_dir" submodule sync --recursive
git -C "$src_dir" submodule update --init --recursive --depth 1 --jobs 8

# ---- Step 2: Run Debian Trixie ARM64 cross-compile ---------------------------
run_build_inside_trixie() {
    bash "$src_dir/runtime/scripts/install-debian-runtime-deps.sh"
    bash "$src_dir/runtime/scripts/build-shadps4-arm64.sh"
}

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
    run_build_inside_trixie
elif command -v docker >/dev/null 2>&1; then
    echo ">> Launching reproducible $builder_image Docker container for ARM64 cross-build..."
    docker run --rm \
        -e BACHATA_INSIDE_DEBIAN_CONTAINER=1 \
        -v "$src_dir:/workspace" \
        -w /workspace \
        "$builder_image" \
        bash -euo pipefail -c '
            bash runtime/scripts/install-debian-runtime-deps.sh
            bash runtime/scripts/build-shadps4-arm64.sh
        '
else
    die "Building shadps4-arm64 requires Debian Trixie or Docker (available on GitHub Actions ubuntu-24.04)."
fi

# ---- Step 3: Stage verified AArch64 ELF binary as bin/kr_core ----------------
built_bin="$src_dir/runtime/build/shadps4-arm64-stage/bin/shadps4-arm64"
needed_txt="$src_dir/runtime/build/shadps4-arm64-stage/needed.txt"
[[ -f "$built_bin" ]] || die "Expected built binary not found: $built_bin"

if command -v readelf >/dev/null 2>&1; then
    hdr=$(readelf -h "$built_bin")
    grep -Eq 'Class:[[:space:]]+ELF64' <<<"$hdr" || die "Built binary is not ELF64"
    grep -Eq 'Machine:[[:space:]]+AArch64' <<<"$hdr" || die "Built binary is not AArch64"
fi

rm -rf "$stage_out"
mkdir -p "$stage_out/bin"
install -m 755 "$built_bin" "$stage_out/bin/kr_core"
if [[ -f "$needed_txt" ]]; then
    cp "$needed_txt" "$stage_out/needed.txt"
fi

echo "=== Phase 4 Runtime Ready: $stage_out/bin/kr_core ==="
ls -lh "$stage_out/bin/kr_core"
