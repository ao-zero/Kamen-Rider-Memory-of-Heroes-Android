# SPDX-License-Identifier: GPL-2.0-or-later
"""
Android ARM64 (nixport) Configuration & Engine Sync Manager
for Kamen Rider: Memory of Heroes (CUSA17374).

Port Lead: AO Zero | Community Partner: Bakka Sub (https://www.bakkasub.my.id)

Responsibilities:
  - Separate read-only bundle path (APP_DIR / $APPDIR) from persistent writable
    storage (DATA_DIR / $HOME/kr_moh, mapped by nixport storage.home).
  - Atomic read/write for launcher.ini, shadPS4 bin/user/config.json, and
    bin/user/input_config/CUSA17374.ini.
  - Mobile-tuned presets (540p / 720p / 1080p, 30 / 60 FPS, FSR + async shaders).
  - Automatic mouse_to_joystick disable when FEXDROID_PRESENT is active so
    virtual touch gamepad right-stick input never conflicts with pointer events.
"""

from __future__ import annotations

import configparser
import io
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple


_WRITE_LOCK = threading.Lock()

# Resolution presets tailored for Snapdragon Adreno 7xx / 8xx GPUs
RES_PRESETS: Dict[str, Tuple[int, int]] = {
    "540p (960x540)": (960, 540),
    "720p (1280x720)": (1280, 720),
    "1080p (1920x1080)": (1920, 1080),
}

RES_ALIASES: Dict[str, str] = {
    "540p": "540p (960x540)",
    "960x540": "540p (960x540)",
    "720p": "720p (1280x720)",
    "1280x720": "720p (1280x720)",
    "1080p": "1080p (1920x1080)",
    "1920x1080": "1080p (1920x1080)",
    "native": "1080p (1920x1080)",
}

# Unity 2017.4 PS4 runs at 2 vblanks per frame: 60 Hz = 30 FPS, 120 Hz = 60 FPS
FPS_VBLANK_MAP: Dict[str, int] = {
    "30 FPS (Locked)": 60,
    "60 FPS (Native Unlock)": 120,
}

FPS_ALIASES: Dict[str, str] = {
    "30": "30 FPS (Locked)",
    "30 fps": "30 FPS (Locked)",
    "30 FPS": "30 FPS (Locked)",
    "60": "60 FPS (Native Unlock)",
    "60 fps": "60 FPS (Native Unlock)",
    "60 FPS": "60 FPS (Native Unlock)",
}

VSYNC_OPTIONS = (
    "Mailbox",
    "Fifo",
    "Immediate",
)

DEVICE_DEFAULTS: Dict[str, str] = {
    "game_dir": "",
    "resolution": "720p (1280x720)",
    "fps": "60 FPS (Native Unlock)",
    "show_fps": "true",
    "fsr_enabled": "true",
    "async_shaders": "true",
    "vsync_mode": "Mailbox",
    "video_backend": "auto",
    "audio_volume": "100",
    "deadzone": "8",
    "indo_patch": "false",
    "language": "id",
    "theme": "dark",
    "player_name": "AO Zero",
}

BOOL_KEYS = (
    "show_fps",
    "fsr_enabled",
    "async_shaders",
    "indo_patch",
)

COMMON_ANDROID_GAME_CANDIDATES = (
    "/storage/emulated/0/Games/CUSA17374",
    "/storage/emulated/0/Games/PS4/CUSA17374",
    "/storage/emulated/0/Download/CUSA17374",
    "/storage/emulated/0/Download/games/ps4/CUSA17374",
    "/sdcard/Games/CUSA17374",
    "/sdcard/Download/CUSA17374",
)


def is_nixport_device() -> bool:
    """Return True when running inside a nixport / fexdroid mobile session."""
    for env_key in ("FEXDROID_PRESENT", "KR_DEVICE_UI", "NIXPORT_PRESENT"):
        val = os.environ.get(env_key, "").strip().lower()
        if val and val not in ("0", "false", "no"):
            return True
    return False


def get_app_dir() -> Path:
    """Read-only application bundle directory (APPDIR inside AppImage or repo root)."""
    for env_key in ("KR_APP_DIR", "APPDIR"):
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            p = Path(env_val)
            if p.exists():
                return p.resolve()
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """Writable persistent user data directory ($HOME/kr_moh, mapped to nixport storage.home)."""
    env_val = os.environ.get("KR_DATA_DIR", "").strip()
    if env_val:
        d = Path(env_val)
    else:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "."
        d = Path(home) / "kr_moh"
    d.mkdir(parents=True, exist_ok=True)
    return d.resolve()


def get_patches_dir(app_dir: Optional[Path] = None) -> Path:
    base = Path(app_dir) if app_dir else get_app_dir()
    return base / "patches"


def get_assets_dir(app_dir: Optional[Path] = None) -> Path:
    base = Path(app_dir) if app_dir else get_app_dir()
    return base / "assets"


def get_ini_path(data_dir: Optional[Path] = None) -> Path:
    return (Path(data_dir) if data_dir else get_data_dir()) / "launcher.ini"


def get_engine_config_path(data_dir: Optional[Path] = None) -> Path:
    return (Path(data_dir) if data_dir else get_data_dir()) / "bin" / "user" / "config.json"


def get_input_config_dir(data_dir: Optional[Path] = None) -> Path:
    return (Path(data_dir) if data_dir else get_data_dir()) / "bin" / "user" / "input_config"


def get_log_dir(data_dir: Optional[Path] = None) -> Path:
    d = (Path(data_dir) if data_dir else get_data_dir()) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_data_layout(data_dir: Optional[Path] = None) -> Path:
    """Create all writable subdirectories under DATA_DIR."""
    d = Path(data_dir) if data_dir else get_data_dir()
    for rel in (
        Path("logs"),
        Path("saves_backup"),
        Path("bin") / "user" / "log",
        Path("bin") / "user" / "input_config",
        Path("bin") / "user" / "vanilla_backup",
        Path("bin") / "user" / "cache",
        Path("bin") / "user" / "home" / "1000" / "savedata" / "CUSA17374",
    ):
        (d / rel).mkdir(parents=True, exist_ok=True)
    return d


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def _read_json_tolerant(path: Path) -> dict:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace").lstrip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}


def resolve_game_dir(candidate: str | Path) -> Optional[Path]:
    """Validate a folder (or its CUSA17374 child) contains eboot.bin."""
    if not candidate:
        return None
    p = Path(candidate)
    if (p / "eboot.bin").is_file():
        return p
    if (p / "CUSA17374" / "eboot.bin").is_file():
        return p / "CUSA17374"
    return None


def auto_detect_game_dir(app_dir: Optional[Path] = None) -> str:
    """Scan common Android/local paths for an existing CUSA17374 dump."""
    env_dir = os.environ.get("KR_GAME_DIR", "").strip()
    if env_dir:
        found = resolve_game_dir(env_dir)
        if found:
            return str(found)

    candidates = list(COMMON_ANDROID_GAME_CANDIDATES)
    if app_dir:
        candidates.append(str(Path(app_dir) / "CUSA17374"))
    for raw in candidates:
        found = resolve_game_dir(raw)
        if found:
            return str(found)
    return ""


def normalize_config(cfg: Dict[str, str]) -> Dict[str, str]:
    """Normalize aliases, booleans, and numeric ranges."""
    out = dict(DEVICE_DEFAULTS)
    for k, v in cfg.items():
        if v is not None:
            out[k] = str(v).strip()

    res_val = out.get("resolution", DEVICE_DEFAULTS["resolution"])
    if res_val in RES_ALIASES:
        out["resolution"] = RES_ALIASES[res_val]
    elif res_val.lower() in RES_ALIASES:
        out["resolution"] = RES_ALIASES[res_val.lower()]
    elif res_val not in RES_PRESETS:
        out["resolution"] = DEVICE_DEFAULTS["resolution"]

    fps_val = out.get("fps", DEVICE_DEFAULTS["fps"])
    if fps_val in FPS_ALIASES:
        out["fps"] = FPS_ALIASES[fps_val]
    elif fps_val.lower() in FPS_ALIASES:
        out["fps"] = FPS_ALIASES[fps_val.lower()]
    elif fps_val not in FPS_VBLANK_MAP:
        out["fps"] = DEVICE_DEFAULTS["fps"]

    vsync = out.get("vsync_mode", "Mailbox")
    matched_vsync = next((v for v in VSYNC_OPTIONS if v.lower() == vsync.lower()), "Mailbox")
    out["vsync_mode"] = matched_vsync

    if out.get("language", "id").lower() not in ("id", "en"):
        out["language"] = "id"
    else:
        out["language"] = out["language"].lower()

    if out.get("theme", "dark").lower() not in ("dark", "light"):
        out["theme"] = "dark"
    else:
        out["theme"] = out["theme"].lower()

    if out.get("video_backend", "auto").lower() not in ("auto", "x11", "wayland"):
        out["video_backend"] = "auto"
    else:
        out["video_backend"] = out["video_backend"].lower()

    for bkey in BOOL_KEYS:
        raw_b = out.get(bkey, DEVICE_DEFAULTS[bkey]).lower()
        out[bkey] = "true" if raw_b in ("1", "true", "yes", "on") else "false"

    try:
        vol = max(0, min(100, int(float(out.get("audio_volume", "100")))))
    except (TypeError, ValueError):
        vol = 100
    out["audio_volume"] = str(vol)

    try:
        dz = max(1, min(30, int(float(out.get("deadzone", "8")))))
    except (TypeError, ValueError):
        dz = 8
    out["deadzone"] = str(dz)

    return out


def load_android_config(data_dir: Optional[Path] = None, app_dir: Optional[Path] = None) -> Dict[str, str]:
    """Load launcher.ini from DATA_DIR, applying mobile defaults and env overrides."""
    d = ensure_data_layout(data_dir)
    ini_path = get_ini_path(d)
    raw: Dict[str, str] = dict(DEVICE_DEFAULTS)

    if ini_path.is_file():
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(ini_path, encoding="utf-8")
            if "Launcher" in parser:
                for k, v in parser["Launcher"].items():
                    raw[k] = v
        except Exception as exc:
            print(f"[ANDROID-CFG] Warning reading {ini_path}: {exc}")

    cfg = normalize_config(raw)

    # Auto-detect game_dir if currently empty
    if not cfg.get("game_dir"):
        detected = auto_detect_game_dir(app_dir)
        if detected:
            cfg["game_dir"] = detected

    return cfg


def save_android_config(data_dir: Optional[Path], cfg: Dict[str, str]) -> Dict[str, str]:
    """Atomically save normalized config to DATA_DIR/launcher.ini."""
    d = ensure_data_layout(data_dir)
    normalized = normalize_config(cfg)
    ini_path = get_ini_path(d)

    parser = configparser.ConfigParser(interpolation=None)
    parser["Launcher"] = {k: str(v) for k, v in normalized.items()}
    buf = io.StringIO()
    parser.write(buf)

    with _WRITE_LOCK:
        _atomic_write_text(ini_path, buf.getvalue())

    return normalized


def sync_android_engine_config(data_dir: Optional[Path], cfg: Dict[str, str]) -> Path:
    """Write mobile-optimized shadPS4 config.json & input_config under DATA_DIR."""
    d = ensure_data_layout(data_dir)
    normalized = normalize_config(cfg)
    cfg_path = get_engine_config_path(d)

    int_w, int_h = RES_PRESETS.get(normalized["resolution"], (1280, 720))
    target_vblank = FPS_VBLANK_MAP.get(normalized["fps"], 120)
    show_fps = normalized["show_fps"] == "true"
    fsr_enabled = normalized["fsr_enabled"] == "true" or normalized["resolution"].startswith("540p")
    async_shaders = normalized["async_shaders"] == "true"
    volume = int(normalized["audio_volume"])
    on_device = is_nixport_device()

    with _WRITE_LOCK:
        engine_cfg = _read_json_tolerant(cfg_path)

        gpu = engine_cfg.setdefault("GPU", {})
        gpu["window_width"] = int_w
        gpu["window_height"] = int_h
        gpu["internal_screen_width"] = int_w
        gpu["internal_screen_height"] = int_h
        gpu["full_screen"] = True
        gpu["full_screen_mode"] = "Borderless"
        gpu["present_mode"] = normalized["vsync_mode"]
        gpu["vblank_frequency"] = target_vblank
        gpu["async_shader_compilation"] = async_shaders
        gpu["fast_shader_math"] = True
        gpu["direct_memory_access_enabled"] = True
        gpu["fsr_enabled"] = fsr_enabled
        gpu["rcas_enabled"] = fsr_enabled
        gpu["rcas_attenuation"] = 250
        gpu["aspect_ratio"] = "16:9"
        gpu["dump_shaders"] = False

        vulkan = engine_cfg.setdefault("Vulkan", {})
        vulkan["vkvalidation_core_enabled"] = False
        vulkan["vkvalidation_enabled"] = False
        vulkan["vkvalidation_gpu_enabled"] = False
        vulkan["vkvalidation_sync_enabled"] = False
        vulkan["pipeline_cache_enabled"] = True
        vulkan["pipeline_cache_archived"] = True

        gen = engine_cfg.setdefault("General", {})
        gen["show_fps_counter"] = show_fps
        gen["show_splash"] = False
        gen["dev_kit_mode"] = False
        gen["volume_slider"] = volume
        # Mobile-friendly pool sizes for 8-12 GB Android devices
        gen["extra_dmem_in_mbytes"] = 1024
        gen["extra_fmem_in_mbytes"] = 512

        log = engine_cfg.setdefault("Log", {})
        log["sync"] = False
        log["enable"] = False
        log["skip_duplicate"] = True

        inp = engine_cfg.setdefault("Input", {})
        inp["use_keyboard_as_keyboard"] = False
        inp["use_mice_as_mice"] = False
        inp["use_unified_input_config"] = True
        inp["cursor_hide_timeout"] = 0
        inp["background_controller_input"] = True
        if on_device:
            # Never hijack right analog stick with mouse events when virtual touch gamepad is active
            inp["mouse_to_joystick"] = "none"

        _atomic_write_text(cfg_path, json.dumps(engine_cfg, indent=2) + "\n")

    sync_android_input_config(d, normalized, disable_mouse_look=on_device)
    return cfg_path


def sync_android_input_config(
    data_dir: Path,
    cfg: Dict[str, str],
    disable_mouse_look: Optional[bool] = None,
) -> Path:
    """Write CUSA17374.ini & default.ini tuned for nixport virtual gamepad + Bluetooth controllers."""
    if disable_mouse_look is None:
        disable_mouse_look = is_nixport_device()

    deadzone = int(cfg.get("deadzone", "8"))
    mouse_mode = "none" if disable_mouse_look else "right"

    ini_content = f"""# ==============================================================================
# KAMEN RIDER: MEMORY OF HEROES (CUSA17374) - ANDROID ARM64 INPUT CONFIGURATION
# Port Lead: AO Zero | Community Partner: Bakka Sub (https://www.bakkasub.my.id)
# ==============================================================================

# --- Pointer / Touch Conflict Protection ---
mouse_to_joystick = {mouse_mode}
mouse_movement_params = 0.5, 1.0, 0.1

# --- Gamepad / Virtual Touch Controller Bindings (nixport.virtualkeys.v1) ---
square = square
triangle = triangle
cross = cross
circle = circle

l1 = l1
r1 = r1
l2 = l2
r2 = r2
l3 = l3
r3 = r3

options = options
touchpad_center = back

pad_up = pad_up
pad_down = pad_down
pad_left = pad_left
pad_right = pad_right

# --- Direct Analog Axes Pass-Through ---
axis_left_x = axis_left_x
axis_left_y = axis_left_y
axis_right_x = axis_right_x
axis_right_y = axis_right_y

analog_deadzone = leftjoystick, {deadzone}, 127
analog_deadzone = rightjoystick, {deadzone}, 127

override_controller_color = false, 0, 0, 255
"""
    inp_dir = get_input_config_dir(data_dir)
    inp_dir.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        for fname in ("CUSA17374.ini", "default.ini"):
            _atomic_write_text(inp_dir / fname, ini_content)
    return inp_dir / "CUSA17374.ini"


def find_runtime_binary(app_dir: Optional[Path] = None, data_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate the ARM64 runtime executable (kr_core / shadps4) if bundled."""
    app = Path(app_dir) if app_dir else get_app_dir()
    data = Path(data_dir) if data_dir else get_data_dir()

    candidates = [
        app / "bin" / "kr_core",
        app / "bin" / "shadps4",
        data / "bin" / "kr_core",
        data / "bin" / "shadps4",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def clear_shader_cache(data_dir: Optional[Path] = None) -> dict:
    """Clear Vulkan pipeline & shader cache under DATA_DIR."""
    d = ensure_data_layout(data_dir)
    targets = [
        d / "bin" / "user" / "cache",
        d / "bin" / "user" / "shader_cache",
    ]
    removed_files = 0
    freed_bytes = 0

    for folder in targets:
        if not folder.exists():
            continue
        for item in list(folder.iterdir()):
            try:
                if item.is_file() or item.is_symlink():
                    freed_bytes += item.stat().st_size if item.exists() else 0
                    item.unlink(missing_ok=True)
                    removed_files += 1
                elif item.is_dir():
                    for f in item.rglob("*"):
                        if f.is_file():
                            freed_bytes += f.stat().st_size
                            removed_files += 1
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass

    return {
        "success": True,
        "removed_files": removed_files,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
    }


def render_summary(cfg: Dict[str, str]) -> str:
    """Short render status string matching Clean UI v1.0.0 spec card."""
    res_short = cfg.get("resolution", "720p (1280x720)").split(" ")[0]
    fps_short = "30 FPS" if cfg.get("fps", "").startswith("30") else "60 FPS"
    fsr_label = "FSR" if cfg.get("fsr_enabled") == "true" else "Native"
    return f"{res_short} · {fps_short} · {fsr_label}"
