#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Install Ubuntu 24.04 cross-compile dependencies for Kamen Rider: Memory of Heroes (ARM64)
# Modeled after zFitness/gow3_android packaging/arm-linux/ci-deps.sh
set -euo pipefail

cd -- "$(dirname -- "$0")/../.."
root="$PWD"
prefix="$root/.local-deps/root/usr"
mkdir -p "$prefix/include" "$prefix/share/cmake"

die() { echo "ci-deps: $*" >&2; exit 1; }

if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        clang lld llvm cmake ninja-build pkg-config \
        squashfs-tools glslang-tools \
        libboost-dev robin-map-dev \
        python3 curl git zip unzip ca-certificates xz-utils
fi

# ---- VulkanMemoryAllocator (v3.4.0 header-only) ------------------------------
vma_src="$root/.local-deps/VulkanMemoryAllocator"
if [[ ! -d "$prefix/share/cmake/VulkanMemoryAllocator" ]]; then
    rm -rf "$vma_src"
    git clone -q --depth 1 -b v3.4.0 https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator.git "$vma_src"
    cmake -S "$vma_src" -B "$vma_src/build" -G Ninja \
        -DCMAKE_INSTALL_PREFIX="$prefix" \
        -DVMA_BUILD_DOCUMENTATION=OFF \
        -DVMA_BUILD_SAMPLE=OFF
    cmake --install "$vma_src/build"
fi
echo "ci-deps: VulkanMemoryAllocator ready ($prefix)"

# ---- tsl-robin-map CMake shim (Ubuntu robin-map-dev omits cmake config) ------
tsl_dir="$prefix/share/cmake/tsl-robin-map"
if [[ ! -f "$tsl_dir/tsl-robin-mapConfig.cmake" ]]; then
    mkdir -p "$tsl_dir"
    cat > "$tsl_dir/tsl-robin-mapConfig.cmake" <<'CMAKE'
if(NOT TARGET tsl::robin_map)
    add_library(tsl::robin_map INTERFACE IMPORTED)
    set_target_properties(tsl::robin_map PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "/usr/include")
endif()
set(tsl-robin-map_FOUND TRUE)
CMAKE
fi
echo "ci-deps: tsl-robin-map ready ($tsl_dir)"

# ---- Khronos Vulkan-Headers overlay (newer than Debian Trixie default) -------
vh="$root/.local-deps/Vulkan-Headers"
if [[ ! -d "$vh/include/vulkan" ]]; then
    rm -rf "$vh"
    git clone -q --depth 1 -b vulkan-sdk-1.4.357.0 https://github.com/KhronosGroup/Vulkan-Headers.git "$vh"
fi
echo "ci-deps: Vulkan-Headers ready ($vh)"

# ---- Boost CMake dir diagnostic ----------------------------------------------
boost_dir=$(find /usr/lib /usr/local/lib -maxdepth 3 -type d -name 'Boost-*' -path '*/cmake/*' 2>/dev/null | sort | tail -n 1 || true)
if [[ -n "$boost_dir" ]]; then
    echo "KR_BOOST_DIR=$boost_dir"
fi

echo "ci-deps: all host dependencies installed (headers prefix: $prefix)"
