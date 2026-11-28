# SPDX-License-Identifier: GPL-2.0-or-later
"""
GitHub Releases Update Checker & .nixport.zip Downloader for
Kamen Rider: Memory of Heroes (Android ARM64 Port).

Because nixport mounts the AppImage read-only, updates cannot self-overwrite on disk.
Instead, this module checks GitHub Releases (including pre-releases) and can download
the latest KamenRiderMoH.nixport.<version>.zip directly to /storage/emulated/0/Download
(or DATA_DIR/downloads) so the user can import it in nixport -> Library -> Import Port package.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Callable, Optional


REPO_SLUG = "ao-zero/Kamen-Rider-Memory-of-Heroes-Android"
RELEASES_API = f"https://api.github.com/repos/{REPO_SLUG}/releases?per_page=5"
RELEASES_URL = f"https://github.com/{REPO_SLUG}/releases"
USER_AGENT = "KR-Memory-of-Heroes-Android-Launcher/1.0.0"


def parse_version_tuple(raw: str) -> tuple[int, int, int, int, int]:
    """Compare semantic versions including optional -alpha.N / -beta.N / -rc.N tags."""
    s = str(raw or "").strip().lstrip("vV")
    m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.?(\d+)?)?", s, re.IGNORECASE)
    if not m:
        return (0, 0, 0, 0, 0)
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    stage = (m.group(4) or "").lower()
    stage_num = int(m.group(5) or 0)
    # Stable (empty stage) ranks higher than rc > beta > alpha
    stage_rank = {"alpha": 1, "beta": 2, "rc": 3, "": 4}.get(stage, 0)
    return (major, minor, patch, stage_rank, stage_num)


def check_for_updates(current_version: str, include_prereleases: bool = True) -> dict:
    """Query GitHub Releases API and return the newest matching release metadata."""
    try:
        req = urllib.request.Request(RELEASES_API, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as resp:
            releases = json.loads(resp.read().decode("utf-8"))

        if not isinstance(releases, list) or not releases:
            return {
                "success": True,
                "current": current_version,
                "latest": current_version,
                "up_to_date": True,
                "prerelease": False,
                "url": RELEASES_URL,
                "download_url": "",
                "asset_name": "",
                "asset_size_mb": 0.0,
                "message": "No releases published yet.",
            }

        chosen = None
        for rel in releases:
            if rel.get("draft"):
                continue
            if rel.get("prerelease") and not include_prereleases:
                continue
            chosen = rel
            break

        if chosen is None:
            chosen = releases[0]

        latest_tag = str(chosen.get("tag_name") or current_version)
        is_up_to_date = parse_version_tuple(latest_tag) <= parse_version_tuple(current_version)

        download_url = ""
        asset_name = ""
        asset_size_mb = 0.0
        for asset in chosen.get("assets", []):
            name = str(asset.get("name", ""))
            if name.lower().endswith(".zip"):
                download_url = str(asset.get("browser_download_url", ""))
                asset_name = name
                asset_size_mb = round(int(asset.get("size", 0)) / (1024 * 1024), 1)
                break

        return {
            "success": True,
            "current": current_version,
            "latest": latest_tag,
            "up_to_date": is_up_to_date,
            "prerelease": bool(chosen.get("prerelease", False)),
            "url": str(chosen.get("html_url") or RELEASES_URL),
            "download_url": download_url,
            "asset_name": asset_name,
            "asset_size_mb": asset_size_mb,
            "message": (
                f"Up to date (v{current_version})"
                if is_up_to_date
                else f"Update available: {latest_tag} ({asset_size_mb} MB)"
            ),
        }
    except Exception as exc:
        return {
            "success": False,
            "current": current_version,
            "latest": current_version,
            "up_to_date": True,
            "prerelease": False,
            "url": RELEASES_URL,
            "download_url": "",
            "asset_name": "",
            "asset_size_mb": 0.0,
            "message": f"Update check unavailable: {exc}",
        }


def default_download_dir(data_dir: Path) -> Path:
    android_dl = Path("/storage/emulated/0/Download")
    if android_dl.is_dir() and os.access(android_dl, os.W_OK):
        return android_dl
    out = Path(data_dir) / "downloads"
    out.mkdir(parents=True, exist_ok=True)
    return out


def download_port_zip(
    download_url: str,
    asset_name: str,
    dest_dir: Path,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """Stream the updated .nixport.zip file safely to dest_dir."""
    if not download_url:
        return {"success": False, "path": "", "message": "No download URL provided."}

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(asset_name or "KamenRiderMoH.nixport.zip").name
    dest_file = dest_dir / safe_name
    tmp_file = dest_file.with_suffix(".zip.part")

    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp_file, "wb") as out_f:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    done += len(chunk)
                    if progress_cb and total > 0:
                        pct = min(100, int(done * 100 / total))
                        progress_cb(pct, f"Downloading {safe_name}: {pct}% ({done / 1048576:.1f}/{total / 1048576:.1f} MB)")
        os.replace(tmp_file, dest_file)
        return {
            "success": True,
            "path": str(dest_file),
            "message": f"Downloaded to {dest_file}. Import it via nixport -> Library -> Import Port package.",
        }
    except Exception as exc:
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass
        return {"success": False, "path": "", "message": f"Download failed: {exc}"}
