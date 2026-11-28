# SPDX-License-Identifier: GPL-2.0-or-later
"""
Android / Linux Device Hardware Probe, Shader Cache Stats, Auto-Preset Advisor,
and 1-Click Diagnostic ZIP Bundle Exporter for Kamen Rider: Memory of Heroes (CUSA17374).
Zero external dependencies (Pure Python stdlib).
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, List


def _run_getprop(prop: str) -> str:
    gp = shutil.which("getprop")
    if not gp:
        return ""
    try:
        out = subprocess.check_output([gp, prop], stderr=subprocess.DEVNULL, timeout=1.5)
        return out.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def _read_ram_gb() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        try:
            for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return round(kb / (1024 * 1024), 1)
        except Exception:
            pass
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass
    return 0.0


def _detect_soc_and_device() -> tuple[str, str]:
    brand = _run_getprop("ro.product.brand")
    model = _run_getprop("ro.product.model")
    soc = _run_getprop("ro.soc.model") or _run_getprop("ro.board.platform") or _run_getprop("ro.hardware")

    if not soc and Path("/proc/cpuinfo").is_file():
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith(("hardware", "model name")):
                    val = line.split(":", 1)[1].strip()
                    if val:
                        soc = val
                        break
        except Exception:
            pass

    if not soc:
        soc = platform.processor() or platform.machine() or "Unknown CPU"

    device = f"{brand} {model}".strip() if (brand or model) else f"{platform.system()} {platform.machine()}"
    return soc, device


def _detect_vulkan_icds() -> List[str]:
    icds: List[str] = []
    env_icd = os.environ.get("VK_ICD_FILENAMES", "").strip()
    if env_icd:
        icds.extend(p for p in env_icd.split(os.pathsep) if p)
    fxd_root = Path(os.environ.get("FXD_ROOT", "/data/user/0/ro.cobrabm.fexdroid/files/rootfs"))
    for d in (Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d"), fxd_root / "usr/share/vulkan/icd.d"):
        if d.is_dir():
            for p in sorted(d.glob("*.json")):
                s = str(p)
                if s not in icds:
                    icds.append(s)
    return icds


def get_shader_cache_stats(data_dir: Path) -> dict:
    """Count files and total MB inside shadPS4 cache directories under DATA_DIR."""
    d = Path(data_dir)
    targets = (
        d / "bin" / "user" / "cache",
        d / "bin" / "user" / "shader_cache",
    )
    total_files = 0
    total_bytes = 0
    for folder in targets:
        if not folder.exists():
            continue
        for f in folder.rglob("*"):
            if f.is_file():
                try:
                    total_bytes += f.stat().st_size
                    total_files += 1
                except Exception:
                    pass
    size_mb = round(total_bytes / (1024 * 1024), 2)
    return {
        "files": total_files,
        "size_mb": size_mb,
        "summary": f"{size_mb:.1f} MB · {total_files} files" if total_files else "Empty (0.0 MB)",
    }


def recommend_mobile_preset(hw: dict) -> dict:
    """Suggest resolution, FPS, and FSR settings based on detected RAM and SoC."""
    ram_gb = float(hw.get("ram_gb", 0.0) or 0.0)
    soc_l = str(hw.get("soc", "")).lower()

    flagship_tokens = ("sm8550", "sm8650", "sm8750", "gen 2", "gen 3", "elite", "8g2", "8g3")
    is_flagship = any(tok in soc_l for tok in flagship_tokens) or ram_gb >= 11.0

    if is_flagship:
        return {
            "name": "Balanced 720p (60 FPS + FSR)",
            "resolution": "720p (1280x720)",
            "fps": "60 FPS (Native Unlock)",
            "fsr_enabled": "true",
            "async_shaders": "true",
        }
    return {
        "name": "Performance 540p (30 FPS + FSR)",
        "resolution": "540p (960x540)",
        "fps": "30 FPS (Locked)",
        "fsr_enabled": "true",
        "async_shaders": "true",
    }


def _probe_vulkan_driver() -> tuple[str, bool]:
    """Run fast vulkaninfo --summary if available to verify Vulkan 1.3 / Turnip is active."""
    fxd_root = Path(os.environ.get("FXD_ROOT", "/data/user/0/ro.cobrabm.fexdroid/files/rootfs"))
    vkinfo = shutil.which("vulkaninfo")
    loader = fxd_root / "usr" / "lib" / "aarch64-linux-gnu" / "ld-linux-aarch64.so.1"
    fxd_vkinfo = fxd_root / "usr" / "bin" / "vulkaninfo"

    cmd = None
    env = dict(os.environ)
    env.pop("LD_PRELOAD", None)
    if fxd_vkinfo.is_file() and loader.is_file():
        lib_dir = str(fxd_root / "usr" / "lib" / "aarch64-linux-gnu")
        env["LD_LIBRARY_PATH"] = f"{lib_dir}:{env.get('LD_LIBRARY_PATH', '')}".rstrip(":")
        cmd = [str(loader), str(fxd_vkinfo), "--summary"]
    elif vkinfo:
        cmd = [vkinfo, "--summary"]

    if not cmd:
        return ("", True)

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=env, timeout=2.5).decode("utf-8", "replace")
        api_ver = ""
        drv_name = ""
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("apiVersion") and "=" in s:
                api_ver = s.split("=", 1)[1].strip().split()[-1].strip("()")
            elif s.startswith("driverName") and "=" in s:
                drv_name = s.split("=", 1)[1].strip()
        if drv_name or api_ver:
            ok_13 = not api_ver.startswith(("1.0", "1.1", "1.2"))
            return (f"{drv_name or 'Vulkan'} ({api_ver or 'active'})".strip(), ok_13)
    except Exception:
        pass
    return ("", True)


def detect_device_hardware(data_dir: Path) -> dict:
    """Collect a safe cross-platform hardware summary for Android/Linux/Windows testing."""
    soc, device = _detect_soc_and_device()
    ram_gb = _read_ram_gb()
    icds = _detect_vulkan_icds()
    vk_probe_label, vk_13_ok = _probe_vulkan_driver()

    try:
        usage = shutil.disk_usage(str(data_dir))
        free_gb = round(usage.free / (1024 ** 3), 1)
        total_gb = round(usage.total / (1024 ** 3), 1)
        disk_text = f"{free_gb} GB free / {total_gb} GB"
    except Exception:
        disk_text = "Unknown"

    turnip_active = any("turnip" in i.lower() or "freedreno" in i.lower() for i in icds) or (
        "turnip" in vk_probe_label.lower()
    )
    if vk_probe_label:
        vulkan_summary = vk_probe_label
    elif turnip_active:
        vulkan_summary = "Turnip / Freedreno ICD detected"
    elif icds:
        vulkan_summary = f"{len(icds)} Vulkan ICD(s) detected"
    else:
        vulkan_summary = "Host Vulkan Bridge"

    hw = {
        "device": device,
        "soc": soc,
        "arch": platform.machine() or "aarch64",
        "ram_gb": ram_gb,
        "os": f"{platform.system()} {platform.release()}",
        "disk_free": disk_text,
        "vulkan_summary": vulkan_summary,
        "vulkan_13_ok": vk_13_ok,
        "vulkan_icds": icds,
        "turnip_detected": turnip_active,
        "fexdroid_present": bool(os.environ.get("FEXDROID_PRESENT")),
    }
    preset = recommend_mobile_preset(hw)
    hw["recommended"] = preset["name"]
    hw["recommended_preset"] = preset
    return hw


def format_specs_clipboard(hw: dict, version: str, cache_stats: dict) -> str:
    return (
        f"Kamen Rider: Memory of Heroes (Android Port v{version})\n"
        f"Device      : {hw.get('device', 'Unknown')}\n"
        f"SoC / CPU   : {hw.get('soc', 'Unknown')} ({hw.get('arch', 'aarch64')})\n"
        f"RAM         : {hw.get('ram_gb', 0)} GB\n"
        f"OS / Kernel : {hw.get('os', 'Unknown')}\n"
        f"Storage     : {hw.get('disk_free', 'Unknown')}\n"
        f"Vulkan ICD  : {hw.get('vulkan_summary', 'Unknown')}\n"
        f"Shader Cache: {cache_stats.get('summary', '0.0 MB')}\n"
        f"Recommended : {hw.get('recommended', '540p')}"
    )


def default_diagnostic_dir(data_dir: Path) -> Path:
    android_dl = Path("/storage/emulated/0/Download")
    if android_dl.is_dir() and os.access(android_dl, os.W_OK):
        return android_dl
    out = Path(data_dir) / "diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    return out


def export_diagnostic_bundle(
    data_dir: Path,
    dest_zip: Path,
    hardware_info: dict,
    current_version: str,
    game_dir: Path | None,
) -> dict:
    """Package device specs, launcher settings, engine config, session stats, and logs into a .zip."""
    data_dir = Path(data_dir)
    dest_zip = Path(dest_zip)

    try:
        dest_zip.parent.mkdir(parents=True, exist_ok=True)
        if game_dir and (Path(game_dir) / "eboot.bin").is_file():
            eboot = Path(game_dir) / "eboot.bin"
            eboot_status = f"FOUND ({round(eboot.stat().st_size / (1024 * 1024), 2)} MB)"
        else:
            eboot_status = "MISSING"

        hw = hardware_info or {}
        cache_stats = get_shader_cache_stats(data_dir)
        specs_lines = [
            "======================================================================",
            " KAMEN RIDER: MEMORY OF HEROES (ANDROID ARM64) DIAGNOSTIC REPORT",
            "======================================================================",
            f"Generated At       : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Port Version       : {current_version}",
            f"DATA_DIR           : {data_dir}",
            f"Game Directory     : {game_dir or 'Not selected'}",
            f"eboot.bin Status   : {eboot_status}",
            "----------------------------------------------------------------------",
            f"Device             : {hw.get('device', 'Unknown')}",
            f"SoC / CPU          : {hw.get('soc', 'Unknown')} ({hw.get('arch', 'aarch64')})",
            f"RAM                : {hw.get('ram_gb', 0)} GB",
            f"OS / Kernel        : {hw.get('os', 'Unknown')}",
            f"Storage            : {hw.get('disk_free', 'Unknown')}",
            f"Vulkan ICD         : {hw.get('vulkan_summary', 'Unknown')}",
            f"FEXDROID_PRESENT   : {hw.get('fexdroid_present', False)}",
            f"Shader Cache       : {cache_stats.get('summary', 'Empty')}",
            f"Recommended Preset : {hw.get('recommended', 'Unknown')}",
            "======================================================================",
        ]

        candidates = [
            (data_dir / "launcher.ini", "launcher.ini"),
            (data_dir / "bin" / "user" / "config.json", "engine_config.json"),
            (data_dir / "bin" / "user" / "input_config" / "CUSA17374.ini", "input_CUSA17374.ini"),
            (data_dir / "bin" / "user" / "session_stats.json", "session_stats.json"),
            (data_dir / "bin" / "user" / "vanilla_backup" / "patch_state.json", "patch_state.json"),
            (data_dir / "logs" / "launch.log", "logs/launch.log"),
            (data_dir / "bin" / "user" / "log" / "shad_log.txt", "logs/shad_log.txt"),
            (data_dir / "bin" / "user" / "log" / "shadps4.log", "logs/shadps4.log"),
        ]

        included = ["system_specs.txt"]
        with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("system_specs.txt", "\n".join(specs_lines) + "\n")
            for src, arcname in candidates:
                if src.is_file():
                    try:
                        zf.write(src, arcname=arcname)
                        included.append(arcname)
                    except Exception:
                        pass
            manifest = {
                "version": current_version,
                "files": included,
                "hardware": hw,
                "shader_cache": cache_stats,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")

        size_kb = round(dest_zip.stat().st_size / 1024, 1)
        return {
            "success": True,
            "path": str(dest_zip),
            "count": len(included),
            "message": f"Diagnostic ZIP exported ({len(included)} files, {size_kb} KB): {dest_zip.name}",
        }
    except Exception as exc:
        return {
            "success": False,
            "path": "",
            "count": 0,
            "message": f"Failed to export diagnostic ZIP: {exc}",
        }
