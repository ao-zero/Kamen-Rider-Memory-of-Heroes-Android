#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
entry_main.py — JSON contract handler for `entry.sh` verbs (`config`, `info`, `check`, `sync`).
Modeled after zFitness/gow3_android `packaging/arm-linux/entry_main.py` so the nixport
Android host app can inspect port metadata and render dynamic configuration cards.

Usage:
  entry_main.py config schema                 <launcher.ini>
  entry_main.py config get                    <launcher.ini>
  entry_main.py config set <payload-json>     <launcher.ini>
  entry_main.py info [summary|patches]        <launcher.ini>
  entry_main.py check                         <launcher.ini>
  entry_main.py sync                          <launcher.ini>
  entry_main.py get-game-dir                  <launcher.ini>
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
_CANDIDATE_ROOTS = (_THIS.parent, _THIS.parent.parent.parent)
for _root in _CANDIDATE_ROOTS:
    if (_root / "scripts").is_dir() and str(_root / "scripts") not in sys.path:
        sys.path.insert(0, str(_root / "scripts"))

import android_config as acfg  # noqa: E402
import indo_patcher  # noqa: E402
import sfo_parser  # noqa: E402


PORT_ID = "kamen-rider-moh"
PORT_NAME = "Kamen Rider: Memory of Heroes"
PORT_VERSION = "1.0.0"
TITLE_ID = "CUSA17374"


def _resolve_dirs(ini_arg: str | None) -> tuple[Path, Path, Path]:
    app_dir = acfg.get_app_dir()
    if ini_arg:
        data_dir = Path(ini_arg).resolve().parent
    else:
        data_dir = acfg.get_data_dir()
    patches_dir = acfg.get_patches_dir(app_dir)
    return app_dir, data_dir, patches_dir


def _build_schema(cfg: dict, data_dir: Path, patches_dir: Path) -> dict:
    groups = [
        {
            "id": "game",
            "title": "Game (CUSA17374)",
            "items": [
                {
                    "key": "game_dir",
                    "title": "Game Directory",
                    "type": "file",
                    "mode": "directory",
                    "note": "Folder containing CUSA17374/eboot.bin (e.g. /storage/emulated/0/Games/CUSA17374)",
                }
            ],
        },
        {
            "id": "display",
            "title": "Graphics & Performance",
            "items": [
                {
                    "key": "resolution",
                    "title": "Render Resolution",
                    "type": "enum",
                    "enum": ["540p (960x540)", "720p (1280x720)", "1080p (1920x1080)"],
                    "labels": ["540p (960x540)", "720p (1280x720)", "1080p (1920x1080)"],
                    "default": "720p (1280x720)",
                    "restart": True,
                },
                {
                    "key": "fps",
                    "title": "Target Frame Rate",
                    "type": "enum",
                    "enum": ["30 FPS (Locked)", "60 FPS (Native Unlock)"],
                    "labels": ["30 FPS (Locked)", "60 FPS (Native Unlock)"],
                    "default": "60 FPS (Native Unlock)",
                    "restart": True,
                },
                {
                    "key": "show_fps",
                    "title": "Show FPS Counter",
                    "type": "boolean",
                    "default": True,
                    "restart": True,
                },
                {
                    "key": "fsr_enabled",
                    "title": "FSR Upscaling + RCAS",
                    "type": "boolean",
                    "default": True,
                    "restart": True,
                },
                {
                    "key": "async_shaders",
                    "title": "Async Shader Compilation",
                    "type": "boolean",
                    "default": True,
                    "restart": True,
                    "advanced": True,
                },
                {
                    "key": "video_backend",
                    "title": "Video Backend (SDL)",
                    "type": "enum",
                    "enum": ["auto", "x11", "wayland"],
                    "labels": ["Auto", "X11", "Wayland"],
                    "default": "auto",
                    "restart": True,
                    "advanced": True,
                },
            ],
        },
        {
            "id": "ui",
            "title": "Launcher & Localization",
            "items": [
                {
                    "key": "language",
                    "title": "UI Language",
                    "type": "enum",
                    "enum": ["id", "en"],
                    "labels": ["Bahasa Indonesia", "English"],
                    "default": "id",
                },
                {
                    "key": "theme",
                    "title": "Appearance Theme",
                    "type": "enum",
                    "enum": ["dark", "light"],
                    "labels": ["Dark", "Light"],
                    "default": "dark",
                },
            ],
        },
    ]

    # Dynamic patch group appears once a valid CUSA17374 game_dir is configured
    gd = acfg.resolve_game_dir(cfg.get("game_dir", ""))
    if gd is not None:
        st = indo_patcher.get_indo_patch_status(gd, data_dir, patches_dir)
        groups.append(
            {
                "id": "localization",
                "title": "Built-in Patch Bahasa Indonesia",
                "items": [
                    {
                        "key": "indo_patch",
                        "title": f"Bahasa Indonesia — Bakka Sub ({st['translated_count']} strings)",
                        "type": "boolean",
                        "default": False,
                        "restart": True,
                        "note": "Patches CUSA17374/Media/sharedassets0.assets with automatic vanilla backup.",
                    }
                ],
            }
        )

    return {"schema": "nixport.config.v1", "groups": groups}


def _typed_values(cfg: dict) -> dict:
    out = dict(cfg)
    for bkey in acfg.BOOL_KEYS:
        out[bkey] = cfg.get(bkey, "false") == "true"
    out["audio_volume"] = int(cfg.get("audio_volume", "100"))
    out["deadzone"] = int(cfg.get("deadzone", "8"))
    return out


def cmd_config(args: list[str]) -> int:
    if not args:
        print(json.dumps({"error": "missing config subcommand"}))
        return 1

    sub = args[0]
    if sub == "set":
        payload_raw = args[1] if len(args) > 1 else "{}"
        ini_arg = args[2] if len(args) > 2 else None
        app_dir, data_dir, patches_dir = _resolve_dirs(ini_arg)
        cfg = acfg.load_android_config(data_dir, app_dir)
        updates = json.loads(payload_raw)
        if not isinstance(updates, dict):
            raise ValueError("config set payload must be a JSON object")

        want_patch = updates.get("indo_patch")
        for k, v in updates.items():
            if isinstance(v, bool):
                cfg[k] = "true" if v else "false"
            else:
                cfg[k] = str(v)

        cfg = acfg.save_android_config(data_dir, cfg)
        acfg.sync_android_engine_config(data_dir, cfg)

        # Apply/restore Indonesian patch when toggled via nixport card
        gd = acfg.resolve_game_dir(cfg.get("game_dir", ""))
        if isinstance(want_patch, bool) and gd is not None:
            st = indo_patcher.get_indo_patch_status(gd, data_dir, patches_dir)
            if want_patch and not st["applied"]:
                indo_patcher.apply_indo_patch(gd, data_dir, patches_dir)
            elif not want_patch and st["applied"]:
                indo_patcher.restore_vanilla(gd, data_dir)

        print(json.dumps({"values": _typed_values(cfg), "schema": _build_schema(cfg, data_dir, patches_dir)}, ensure_ascii=False))
        return 0

    ini_arg = args[1] if len(args) > 1 else None
    app_dir, data_dir, patches_dir = _resolve_dirs(ini_arg)
    cfg = acfg.load_android_config(data_dir, app_dir)

    if sub == "schema":
        print(json.dumps(_build_schema(cfg, data_dir, patches_dir), ensure_ascii=False))
        return 0
    if sub == "get":
        print(json.dumps({"values": _typed_values(cfg)}, ensure_ascii=False))
        return 0

    print(json.dumps({"error": f"unknown config subcommand: {sub}"}))
    return 1


def cmd_info(args: list[str]) -> int:
    topic = args[0] if args else "summary"
    ini_arg = args[1] if len(args) > 1 else None
    app_dir, data_dir, patches_dir = _resolve_dirs(ini_arg)
    cfg = acfg.load_android_config(data_dir, app_dir)
    gd = acfg.resolve_game_dir(cfg.get("game_dir", ""))
    sfo = sfo_parser.get_game_info(gd) if gd else {}
    patch_st = indo_patcher.get_indo_patch_status(
        gd if gd is not None else (data_dir / "__unset_game_dir__"),
        data_dir,
        patches_dir,
    )
    runtime_bin = acfg.find_runtime_binary(app_dir, data_dir)

    if topic == "patches":
        print(json.dumps({"title_id": TITLE_ID, "indo_patch": patch_st}, ensure_ascii=False))
        return 0

    payload = {
        "schema": "nixport.info.v1",
        "id": PORT_ID,
        "name": PORT_NAME,
        "version": PORT_VERSION,
        "title_id": sfo.get("TITLE_ID", TITLE_ID),
        "app_ver": sfo.get("APP_VER", "01.00"),
        "game_dir": str(gd) if gd else "",
        "game_ready": gd is not None,
        "runtime_ready": runtime_bin is not None,
        "indo_patch": patch_st,
        "data_dir": str(data_dir),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def cmd_check(args: list[str]) -> int:
    ini_arg = args[0] if args else None
    app_dir, data_dir, patches_dir = _resolve_dirs(ini_arg)
    cfg = acfg.load_android_config(data_dir, app_dir)
    gd = acfg.resolve_game_dir(cfg.get("game_dir", ""))
    runtime_bin = acfg.find_runtime_binary(app_dir, data_dir)

    icd_dirs = [
        Path("/usr/share/vulkan/icd.d"),
        Path("/etc/vulkan/icd.d"),
        Path(os.environ.get("FXD_ROOT", "/data/user/0/ro.cobrabm.fexdroid/files/rootfs")) / "usr/share/vulkan/icd.d",
    ]
    icds: list[str] = []
    if os.environ.get("VK_ICD_FILENAMES"):
        icds.append(os.environ["VK_ICD_FILENAMES"])
    for d in icd_dirs:
        if d.is_dir():
            icds.extend(str(p) for p in sorted(d.glob("*.json")))

    report = {
        "eboot_found": gd is not None,
        "game_dir": str(gd) if gd else "",
        "runtime_binary": str(runtime_bin) if runtime_bin else "",
        "patch_dictionary_found": (patches_dir / "id_patch.json").is_file(),
        "vulkaninfo_in_path": shutil.which("vulkaninfo") is not None,
        "vulkan_icds": icds,
        "fexdroid_present": acfg.is_nixport_device(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["eboot_found"] else 1


def main(argv: list[str]) -> int:
    if not argv:
        print(json.dumps({"error": "missing command"}))
        return 1
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "config":
        return cmd_config(rest)
    if cmd == "info":
        return cmd_info(rest)
    if cmd == "check":
        return cmd_check(rest)
    if cmd == "sync":
        app_dir, data_dir, _ = _resolve_dirs(rest[0] if rest else None)
        cfg = acfg.load_android_config(data_dir, app_dir)
        acfg.sync_android_engine_config(data_dir, cfg)
        return 0
    if cmd == "get-game-dir":
        app_dir, data_dir, _ = _resolve_dirs(rest[0] if rest else None)
        cfg = acfg.load_android_config(data_dir, app_dir)
        gd = acfg.resolve_game_dir(cfg.get("game_dir", ""))
        print(str(gd) if gd else "")
        return 0
    if cmd == "get-key":
        key = rest[0] if rest else ""
        ini_arg = rest[1] if len(rest) > 1 else None
        app_dir, data_dir, _ = _resolve_dirs(ini_arg)
        cfg = acfg.load_android_config(data_dir, app_dir)
        print(cfg.get(key, ""))
        return 0

    print(json.dumps({"error": f"unknown command: {cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
