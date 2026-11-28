# SPDX-License-Identifier: GPL-2.0-or-later
"""
Guest-side bridge to nixport's host service bus (/usr/local/bin/nxp-port)
for native Android touch directory & file pickers and toast notifications.
Automatically falls back to None when running outside nixport (desktop testing).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Iterable, Optional

NXP_PORT = "nxp-port"
EXIT_OK = 0
EXIT_CANCELLED = 9
EXIT_NO_BUS = (3, 4, 5)


def _rootfs_paths() -> list[str]:
    paths: list[str] = []
    rootfs = os.environ.get("FXD_ROOT", "").strip()
    if rootfs:
        paths.append(rootfs)
    found = shutil.which(NXP_PORT)
    if found:
        marker = os.path.join("usr", "local", "bin", NXP_PORT)
        idx = found.find(marker)
        if idx > 0:
            paths.append(found[:idx].rstrip("/\\"))
    default_fxd = "/data/user/0/ro.cobrabm.fexdroid/files/rootfs"
    if default_fxd not in paths and os.path.isdir(default_fxd):
        paths.append(default_fxd)
    return paths


def _candidates(action: str, arguments: list[str]):
    for rootfs in _rootfs_paths():
        tool = os.path.join(rootfs, "usr", "local", "bin", NXP_PORT)
        python_bin = os.path.join(rootfs, "usr", "bin", "python3.13")
        loader = os.path.join(rootfs, "usr", "lib", "aarch64-linux-gnu", "ld-linux-aarch64.so.1")
        if os.path.exists(tool) and os.path.exists(python_bin):
            if os.path.exists(loader):
                yield [loader, python_bin, tool, action, *arguments]
            yield [python_bin, tool, action, *arguments]
    found = shutil.which(NXP_PORT)
    if found:
        yield [found, action, *arguments]


def available() -> bool:
    """Return True when the nixport host bus socket and nxp-port client are reachable."""
    if not os.environ.get("NXP_HOST_SOCKET"):
        return False
    for rootfs in _rootfs_paths():
        if os.path.exists(os.path.join(rootfs, "usr", "local", "bin", NXP_PORT)):
            return True
    return shutil.which(NXP_PORT) is not None


def _run(action: str, arguments: list[str]) -> Optional[str]:
    env = dict(os.environ)
    env.pop("LD_PRELOAD", None)
    for rootfs in _rootfs_paths():
        lib_dir = os.path.join(rootfs, "usr", "lib", "aarch64-linux-gnu")
        if os.path.isdir(lib_dir):
            env["LD_LIBRARY_PATH"] = f"{lib_dir}:{env.get('LD_LIBRARY_PATH', '')}".rstrip(":")
            break

    for command in _candidates(action, arguments):
        try:
            done = subprocess.run(command, capture_output=True, text=True, env=env, timeout=180)
        except Exception:
            continue
        if done.returncode in EXIT_NO_BUS:
            return None
        if done.returncode == EXIT_CANCELLED:
            return ""
        if done.returncode != EXIT_OK:
            return None
        return done.stdout.strip()
    return None


def pick_directory(initial: Optional[str] = None) -> Optional[str]:
    """Open Android native directory picker via nixport bus.
    Returns chosen path, '' on user cancel, or None if host bus is unavailable."""
    if not available():
        return None
    args = ["--initial", initial] if initial else []
    return _run("pick-dir", args)


def pick_file(initial: Optional[str] = None, extensions: Iterable[str] = ()) -> Optional[str]:
    """Open Android native file picker via nixport bus.
    Returns chosen path, '' on user cancel, or None if host bus is unavailable."""
    if not available():
        return None
    args: list[str] = []
    if initial:
        args += ["--initial", initial]
    for ext in extensions:
        args += ["--ext", ext.lstrip(".")]
    return _run("pick-file", args)


def toast(message: str) -> bool:
    """Show a native Android toast notification if host bus is available."""
    if not available():
        return False
    return _run("toast", [message]) is not None
