# SPDX-License-Identifier: GPL-2.0-or-later
# CMake cross-compilation toolchain for ARM64 Linux (aarch64-linux-gnu / nixport)
# Modeled after zFitness/gow3_android packaging/arm-linux/cross-toolchain.cmake

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

if(NOT DEFINED KR_ARM64_SYSROOT)
  if(DEFINED ENV{KR_ARM64_SYSROOT} AND NOT "$ENV{KR_ARM64_SYSROOT}" STREQUAL "")
    set(KR_ARM64_SYSROOT "$ENV{KR_ARM64_SYSROOT}")
  else()
    get_filename_component(_repo_root "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
    set(KR_ARM64_SYSROOT "${_repo_root}/.local-deps/arm64-sysroot")
  endif()
endif()

if(NOT DEFINED KR_ARM64_HEADER_PREFIX AND DEFINED ENV{KR_ARM64_HEADERS})
  set(KR_ARM64_HEADER_PREFIX "$ENV{KR_ARM64_HEADERS}")
endif()

set(CMAKE_SYSROOT "${KR_ARM64_SYSROOT}")

set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_ASM_COMPILER clang)

# Ensure LLVM archiver/ranlib are used so FEXCore ThinLTO objects link cleanly
if(DEFINED ENV{KR_AR} AND NOT "$ENV{KR_AR}" STREQUAL "")
  set(CMAKE_AR "$ENV{KR_AR}" CACHE FILEPATH "LLVM archiver" FORCE)
  get_filename_component(_llvm_bin "${CMAKE_AR}" DIRECTORY)
  if(EXISTS "${_llvm_bin}/llvm-ranlib")
    set(CMAKE_RANLIB "${_llvm_bin}/llvm-ranlib" CACHE FILEPATH "LLVM ranlib" FORCE)
  endif()
endif()

if(NOT CMAKE_AR)
  find_program(CMAKE_AR NAMES llvm-ar REQUIRED)
endif()
if(NOT CMAKE_RANLIB)
  find_program(CMAKE_RANLIB NAMES llvm-ranlib REQUIRED)
endif()

set(CMAKE_C_COMPILER_AR "${CMAKE_AR}")
set(CMAKE_C_COMPILER_RANLIB "${CMAKE_RANLIB}")
set(CMAKE_CXX_COMPILER_AR "${CMAKE_AR}")
set(CMAKE_CXX_COMPILER_RANLIB "${CMAKE_RANLIB}")

set(CMAKE_C_COMPILER_TARGET aarch64-linux-gnu)
set(CMAKE_CXX_COMPILER_TARGET aarch64-linux-gnu)
set(CMAKE_ASM_COMPILER_TARGET aarch64-linux-gnu)

set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-fuse-ld=lld")

# Libraries come strictly from arm64 sysroot; host code generators (glslang, python) run natively
set(CMAKE_FIND_ROOT_PATH "${KR_ARM64_SYSROOT}" ${KR_ARM64_HEADER_PREFIX})
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)

set(PKG_CONFIG_SYSROOT_DIR "${KR_ARM64_SYSROOT}")
set(ENV{PKG_CONFIG_LIBDIR}
    "${KR_ARM64_SYSROOT}/usr/lib/aarch64-linux-gnu/pkgconfig:${KR_ARM64_SYSROOT}/usr/share/pkgconfig")
