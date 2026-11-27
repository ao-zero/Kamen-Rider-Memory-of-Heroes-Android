#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Fetch a Debian Trixie (13) arm64 sysroot for cross-building the native ARM64
runtime (FEXCore + shadPS4 Vulkan backend) matching nixport's glibc userland.

Every .deb is verified against the SHA-256 digest from Debian's Packages.xz index,
extracted without root privileges, absolute symlinks are rewritten to relative
sysroot-safe links, and modern Khronos Vulkan-Headers are optionally overlaid.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import lzma
import os
import re
import shutil
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Set

DEFAULT_MIRROR = os.environ.get("KR_DEBIAN_MIRROR", "https://deb.debian.org/debian")
SUITE = "trixie"
ARCH = "arm64"

WANTED_PACKAGES = [
    "libc6-dev",
    "libstdc++-14-dev",
    "libgcc-14-dev",
    "linux-libc-dev",
    "libvulkan-dev",
    "libfmt-dev",
    "libxxhash-dev",
    "libsdl3-dev",
    "libx11-dev",
    "libzydis-dev",
    "libavformat-dev",
    "libavcodec-dev",
    "libavutil-dev",
    "libswscale-dev",
    "libswresample-dev",
    "spirv-headers",
    "zlib1g-dev",
    "libxkbcommon-x11-0",
    "libxcb-xkb1",
]

SKIP_PATTERN = re.compile(
    r"^(debconf|perl.*|dpkg|adduser|tzdata|sensible-utils|libc-bin|libc-dev-bin|"
    r"fonts-.*|.*-data|.*-doc|ucf|lsb-base|init-system-helpers|"
    r"python3.*|libpython.*|dbus.*|systemd.*|libsystemd-shared|"
    r"readline-common|mailcap|media-types|netbase|x11-common|coreutils|bash|"
    r"base-files|login|util-linux|mount)$"
)


def fetch_bytes(url: str, attempts: int = 6) -> bytes:
    delay = 2
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kr-moh-sysroot-fetcher/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as exc:
            if attempt == attempts:
                raise
            print(f"  retry {attempt}/{attempts - 1} for {url.rsplit('/', 1)[-1]}: {exc}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise RuntimeError(f"Failed to download {url}")


def parse_packages(text: str) -> Dict[str, dict]:
    packages: Dict[str, dict] = {}
    for block in text.split("\n\n"):
        fields: Dict[str, str] = {}
        key = None
        for line in block.splitlines():
            if line.startswith(" ") and key:
                fields[key] += "\n" + line
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        pkg = fields.get("Package")
        if pkg:
            packages.setdefault(pkg, fields)
            for prov in fields.get("Provides", "").split(","):
                pname = prov.strip().split(" ")[0]
                if pname:
                    packages.setdefault("virtual:" + pname, fields)
    return packages


def extract_dependencies(fields: dict) -> List[str]:
    names: List[str] = []
    for key in ("Pre-Depends", "Depends"):
        for group in fields.get(key, "").split(","):
            group = group.strip()
            if not group:
                continue
            first_alt = group.split("|")[0].strip()
            pkg_name = first_alt.split(" ")[0].split(":")[0].strip()
            if pkg_name:
                names.append(pkg_name)
    return names


def resolve_closure(packages: Dict[str, dict], roots: Iterable[str]) -> List[dict]:
    queue = list(roots)
    seen: Set[str] = set()
    selected: List[dict] = []

    while queue:
        name = queue.pop(0)
        if name in seen or SKIP_PATTERN.match(name):
            continue
        fields = packages.get(name) or packages.get("virtual:" + name)
        if not fields:
            continue
        real_name = fields["Package"]
        if real_name in seen or SKIP_PATTERN.match(real_name):
            continue
        seen.add(real_name)
        seen.add(name)
        selected.append(fields)
        for dep in extract_dependencies(fields):
            if dep not in seen:
                queue.append(dep)
    return selected


def parse_ar_data_member(deb_bytes: bytes) -> tuple[str, bytes]:
    if not deb_bytes.startswith(b"!<arch>\n"):
        raise ValueError("Invalid .deb archive (missing ar magic)")
    pos = 8
    while pos + 60 <= len(deb_bytes):
        header = deb_bytes[pos : pos + 60]
        pos += 60
        name = header[0:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip())
        payload = deb_bytes[pos : pos + size]
        pos += size + (size & 1)
        if name.startswith("data.tar"):
            return name, payload
    raise ValueError("No data.tar.* member found inside .deb")


def extract_deb(deb_bytes: bytes, out_dir: Path) -> None:
    member_name, data_bytes = parse_ar_data_member(deb_bytes)
    mode = "r:*"
    if member_name.endswith(".xz"):
        data_bytes = lzma.decompress(data_bytes)
        mode = "r:"
    with tarfile.open(fileobj=io.BytesIO(data_bytes), mode=mode) as tf:
        for member in tf.getmembers():
            rel = member.name.lstrip("./")
            if not rel or rel.startswith(".."):
                continue
            dest = out_dir / rel
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.issym():
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() or dest.is_symlink():
                    dest.unlink()
                os.symlink(member.linkname, dest)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                if src is not None:
                    with open(dest, "wb") as out_f:
                        shutil.copyfileobj(src, out_f)


def rewrite_absolute_symlinks(sysroot: Path) -> int:
    fixed = 0
    for root, _dirs, files in os.walk(sysroot):
        for fname in files:
            path = Path(root) / fname
            if not path.is_symlink():
                continue
            target = os.readlink(path)
            if target.startswith("/"):
                abs_in_sysroot = sysroot / target.lstrip("/")
                rel_target = os.path.relpath(abs_in_sysroot, path.parent)
                path.unlink()
                os.symlink(rel_target, path)
                fixed += 1
    return fixed


def overlay_vulkan_headers(sysroot: Path, vh_dir: Path) -> None:
    src_inc = vh_dir / "include"
    if not src_inc.is_dir():
        raise FileNotFoundError(f"Vulkan-Headers include directory not found: {src_inc}")
    dst_inc = sysroot / "usr" / "include"
    dst_inc.mkdir(parents=True, exist_ok=True)
    for sub in ("vulkan", "vk_video"):
        if (src_inc / sub).is_dir():
            shutil.copytree(src_inc / sub, dst_inc / sub, dirs_exist_ok=True)
    print(f"[sysroot] Overlaid Vulkan-Headers from {vh_dir}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Debian Trixie arm64 sysroot for cross-building.")
    parser.add_argument("--out", required=True, help="Output sysroot directory")
    parser.add_argument("--mirror", default=DEFAULT_MIRROR, help="Debian mirror base URL")
    parser.add_argument("--vulkan-headers", default="", help="Optional Khronos Vulkan-Headers checkout to overlay")
    parser.add_argument("--jobs", type=int, default=6, help="Parallel download worker count")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    index_url = f"{args.mirror.rstrip('/')}/dists/{SUITE}/main/binary-{ARCH}/Packages.xz"
    print(f"[sysroot] Downloading Debian {SUITE} ({ARCH}) index: {index_url}", flush=True)
    index_raw = lzma.decompress(fetch_bytes(index_url)).decode("utf-8", "replace")
    packages = parse_packages(index_raw)
    closure = resolve_closure(packages, WANTED_PACKAGES)
    print(f"[sysroot] Resolved {len(closure)} packages for arm64 sysroot.", flush=True)

    def download_and_verify(fields: dict) -> tuple[str, bytes]:
        filename = fields["Filename"]
        expected_sha = fields["SHA256"].strip().lower()
        url = f"{args.mirror.rstrip('/')}/{filename}"
        data = fetch_bytes(url)
        actual_sha = hashlib.sha256(data).hexdigest().lower()
        if actual_sha != expected_sha:
            raise ValueError(f"SHA-256 mismatch for {fields['Package']}: {actual_sha} != {expected_sha}")
        return fields["Package"], data

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(download_and_verify, closure))

    for pkg_name, deb_bytes in results:
        extract_deb(deb_bytes, out_dir)
    print(f"[sysroot] Extracted {len(results)} verified .deb archives into {out_dir}", flush=True)

    fixed = rewrite_absolute_symlinks(out_dir)
    print(f"[sysroot] Rewrote {fixed} absolute symlinks for portable sysroot linking.", flush=True)

    if args.vulkan_headers:
        overlay_vulkan_headers(out_dir, Path(args.vulkan_headers).resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
