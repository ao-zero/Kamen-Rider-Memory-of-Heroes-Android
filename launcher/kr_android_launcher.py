#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
================================================================================
  KAMEN RIDER: MEMORY OF HEROES (CUSA17374) — ANDROID ARM64 LAUNCHER (v1.0.0)
  Design: Clean Desktop / Mobile-Adaptive UI (Dark & Light Mode, XSEmu-inspired)
  Port Lead: AO Zero | Community Partner: Bakka Sub (https://www.bakkasub.my.id)
================================================================================
Pure Python stdlib (tkinter) — zero external dependencies, runs natively inside
the nixport ARM64 Linux rootfs as well as Windows/Linux desktop for testing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# Ensure shared scripts directory is importable regardless of working directory
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import android_config as acfg  # noqa: E402
import indo_patcher  # noqa: E402
import save_manager  # noqa: E402
import sfo_parser  # noqa: E402
import trophy_manager  # noqa: E402


VERSION = "1.0.0"

THEMES = {
    "dark": {
        "bg_canvas": "#0B0C0E",
        "bg_sidebar": "#0E0F12",
        "bg_card": "#121418",
        "bg_hover": "#1A1D23",
        "bg_nav_active": "#1A1D24",
        "bg_pill": "#181A20",
        "bg_input": "#0F1115",
        "bg_seg_track": "#181B21",
        "bg_seg_active": "#252933",
        "border": "#20232A",
        "border_strong": "#2E323C",
        "text_primary": "#F3F4F6",
        "text_secondary": "#8E95A2",
        "text_muted": "#5F6673",
        "blue": "#3B66F5",
        "blue_hover": "#2E55E0",
        "blue_soft": "#17203A",
        "blue_text": "#7AA2FF",
        "green_bg": "#11261B",
        "green_text": "#4ADE80",
        "green_dot": "#22C55E",
        "red_bg": "#2B1417",
        "red_text": "#F87171",
        "amber_bg": "#2B2211",
        "amber_text": "#FBBF24",
        "platinum": "#7FB2E5",
        "gold": "#E0B34C",
        "silver": "#C4CBD6",
        "bronze": "#C98A4B",
    },
    "light": {
        "bg_canvas": "#FFFFFF",
        "bg_sidebar": "#FAFAFB",
        "bg_card": "#FFFFFF",
        "bg_hover": "#F3F4F6",
        "bg_nav_active": "#EFEFF2",
        "bg_pill": "#F1F2F5",
        "bg_input": "#FFFFFF",
        "bg_seg_track": "#F3F4F6",
        "bg_seg_active": "#FFFFFF",
        "border": "#E8EAEE",
        "border_strong": "#D5D9E0",
        "text_primary": "#14161A",
        "text_secondary": "#68707D",
        "text_muted": "#8C93A0",
        "blue": "#2F5BFF",
        "blue_hover": "#244CE6",
        "blue_soft": "#EEF2FF",
        "blue_text": "#2F5BFF",
        "green_bg": "#EBF9F0",
        "green_text": "#1B8A4B",
        "green_dot": "#22C55E",
        "red_bg": "#FEF2F2",
        "red_text": "#C93B3B",
        "amber_bg": "#FFFBEB",
        "amber_text": "#B45309",
        "platinum": "#3B76B8",
        "gold": "#B88618",
        "silver": "#6B7280",
        "bronze": "#9C5E26",
    },
}

STRINGS = {
    "id": {
        "nav_play": "Overview",
        "nav_patch": "Patch Indo",
        "nav_saves": "Saves",
        "nav_trophies": "Trophies",
        "nav_settings": "Pengaturan",
        "hero_crumb": "CUSA17374 · Android ARM64 Edition v1.0.0",
        "hero_sub": "Bandai Namco · v{ver} · Port oleh AO Zero & Bakka Sub",
        "btn_play": "Play",
        "btn_running": "Berjalan...",
        "patch_off": "Patch Indo: Off",
        "patch_on": "Patch Indo: Aktif",
        "badge_ready": "Game siap",
        "badge_missing": "Pilih folder game",
        "runs_with": "Runs with",
        "card_game": "GAME",
        "card_engine": "SHADER CACHE & ENGINE",
        "card_log": "ENGINE LOG",
        "card_overrides": "QUICK OVERRIDES",
        "autosaved": "Tersimpan otomatis",
        "lbl_version": "Versi",
        "lbl_subtitle": "Subtitle",
        "lbl_lead": "Port Lead",
        "lbl_folder": "Folder",
        "lbl_state": "Status",
        "lbl_render": "Render",
        "lbl_controller": "Kontrol",
        "lbl_saves": "Save Data",
        "lbl_resolution": "Resolusi",
        "lbl_fps": "Frame rate",
        "lbl_fps_hud": "FPS overlay",
        "lbl_sub_id": "Subtitle ID",
        "btn_verify": "Verifikasi",
        "btn_switch": "Ubah",
        "btn_change": "Pilih",
        "btn_clear_cache": "Hapus cache",
        "btn_clear": "Bersihkan",
        "btn_backup": "Backup",
        "not_set": "Belum dipilih",
        "sub_orig": "Original (EN/JP)",
        "sub_indo": "Bahasa Indonesia (Bakka Sub)",
        "ctrl_touch": "Virtual Touch Gamepad + BT",
        "ctrl_desktop": "Gamepad / Keyboard",
        "patch_title": "Patch Bahasa Indonesia (Bakka Sub)",
        "patch_sub": "Terjemahan penuh menu, tutorial, nama karakter, dan dialog cerita bergaya fansub Bakka Sub.",
        "patch_note": "Backup file original otomatis disimpan di storage persisten (home/kr_moh/bin/user/vanilla_backup/) dan bisa dikembalikan kapan saja.",
        "btn_apply_indo": "Aktifkan Patch Bahasa Indonesia",
        "btn_restore_orig": "Kembalikan ke Original (EN/JP)",
        "patch_busy": "Memproses patch...",
        "saves_title": "Manajer Save Game (CUSA17374)",
        "saves_sub": "Kelola slot penyimpanan portabel dan arsip cadangan .zip di storage persisten nixport.",
        "btn_backup_now": "Buat Backup Save (.zip)",
        "btn_restore_sel": "Pulihkan Backup Terpilih",
        "no_saves": "Belum ada data save CUSA17374 yang terdeteksi.",
        "no_backups": "Belum ada arsip backup save.",
        "trophies_title": "Katalog Trophy PS4 (50 Trophy)",
        "trophies_sub": "Daftar resmi 50 trophy Kamen Rider: Memory of Heroes (1 Platinum, 1 Gold, 10 Silver, 38 Bronze).",
        "filter_all": "Semua",
        "filter_unlocked": "Terbuka",
        "filter_locked": "Terkunci",
        "settings_title": "Pengaturan Mobile & Info Port",
        "settings_sub": "Konfigurasi grafis Vulkan 1.3 (Turnip), input sentuh, tema tampilan, dan informasi storage.",
        "sec_graphics": "GRAFIS & PERFORMA MOBILE",
        "sec_system": "SISTEM, TEMA & STORAGE",
        "sec_credits": "KREDIT & ATRIBUSI",
        "lbl_fsr": "FSR Upscaling + RCAS",
        "lbl_async": "Async Shader Compilation",
        "lbl_vsync": "Mode Present / VSync",
        "lbl_backend": "Video Backend (SDL)",
        "lbl_volume": "Volume Audio",
        "lbl_deadzone": "Deadzone Analog",
        "lbl_theme": "Tema Tampilan",
        "lbl_lang": "Bahasa UI",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "err_no_eboot_title": "eboot.bin Tidak Ditemukan",
        "err_no_eboot_msg": "Folder yang dipilih tidak berisi eboot.bin.\nPilih folder dump CUSA17374 Anda.",
        "err_no_runtime_title": "Runtime ARM64 Belum Terpasang",
        "err_no_runtime_msg": (
            "Binary runtime ARM64 (bin/kr_core) belum ditemukan di paket ini.\n\n"
            "Konfigurasi config.json dan input_config sudah disinkronkan di:\n{data_dir}\n\n"
            "Build paket lengkap dengan GitHub Actions CI (Fase 4: FEXCore + shadPS4 ARM64) "
            "untuk menjalankan game langsung di perangkat Android."
        ),
    },
    "en": {
        "nav_play": "Overview",
        "nav_patch": "Patch Indo",
        "nav_saves": "Saves",
        "nav_trophies": "Trophies",
        "nav_settings": "Settings",
        "hero_crumb": "CUSA17374 · Android ARM64 Edition v1.0.0",
        "hero_sub": "Bandai Namco · v{ver} · Port by AO Zero & Bakka Sub",
        "btn_play": "Play",
        "btn_running": "Running...",
        "patch_off": "Patch Indo: Off",
        "patch_on": "Patch Indo: On",
        "badge_ready": "Game ready",
        "badge_missing": "Select game folder",
        "runs_with": "Runs with",
        "card_game": "GAME",
        "card_engine": "SHADER CACHE & ENGINE",
        "card_log": "ENGINE LOG",
        "card_overrides": "QUICK OVERRIDES",
        "autosaved": "Auto-saved",
        "lbl_version": "Version",
        "lbl_subtitle": "Subtitle",
        "lbl_lead": "Port Lead",
        "lbl_folder": "Folder",
        "lbl_state": "State",
        "lbl_render": "Render",
        "lbl_controller": "Controller",
        "lbl_saves": "Saves",
        "lbl_resolution": "Resolution",
        "lbl_fps": "Frame rate",
        "lbl_fps_hud": "FPS overlay",
        "lbl_sub_id": "Subtitle ID",
        "btn_verify": "Verify",
        "btn_switch": "Switch",
        "btn_change": "Change",
        "btn_clear_cache": "Clear cache",
        "btn_clear": "Clear",
        "btn_backup": "Backup",
        "not_set": "Not selected",
        "sub_orig": "Original (EN/JP)",
        "sub_indo": "Indonesian (Bakka Sub)",
        "ctrl_touch": "Virtual Touch Gamepad + BT",
        "ctrl_desktop": "Gamepad / Keyboard",
        "patch_title": "Indonesian Subtitle Patch (Bakka Sub)",
        "patch_sub": "Full translation of menus, tutorials, character names, and story dialogue in Bakka Sub fansub style.",
        "patch_note": "Original file backup is stored persistently in home/kr_moh/bin/user/vanilla_backup/ and can be restored anytime.",
        "btn_apply_indo": "Enable Indonesian Patch",
        "btn_restore_orig": "Restore Original (EN/JP)",
        "patch_busy": "Applying patch...",
        "saves_title": "Savegame Manager (CUSA17374)",
        "saves_sub": "Manage portable save slots and timestamped .zip backups inside persistent nixport storage.",
        "btn_backup_now": "Create Save Backup (.zip)",
        "btn_restore_sel": "Restore Selected Backup",
        "no_saves": "No CUSA17374 save data detected yet.",
        "no_backups": "No save backup archives yet.",
        "trophies_title": "PS4 Trophy Catalog (50 Trophies)",
        "trophies_sub": "Official 50-trophy list for Kamen Rider: Memory of Heroes (1 Platinum, 1 Gold, 10 Silver, 38 Bronze).",
        "filter_all": "All",
        "filter_unlocked": "Unlocked",
        "filter_locked": "Locked",
        "settings_title": "Mobile Settings & Port Info",
        "settings_sub": "Vulkan 1.3 (Turnip) graphics, touch input protection, theme appearance, and storage paths.",
        "sec_graphics": "MOBILE GRAPHICS & PERFORMANCE",
        "sec_system": "SYSTEM, THEME & STORAGE",
        "sec_credits": "CREDITS & ATTRIBUTION",
        "lbl_fsr": "FSR Upscaling + RCAS",
        "lbl_async": "Async Shader Compilation",
        "lbl_vsync": "Present / VSync Mode",
        "lbl_backend": "Video Backend (SDL)",
        "lbl_volume": "Audio Volume",
        "lbl_deadzone": "Analog Deadzone",
        "lbl_theme": "Appearance Theme",
        "lbl_lang": "UI Language",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "err_no_eboot_title": "eboot.bin Not Found",
        "err_no_eboot_msg": "The selected folder does not contain eboot.bin.\nPlease choose your dumped CUSA17374 directory.",
        "err_no_runtime_title": "ARM64 Runtime Not Bundled",
        "err_no_runtime_msg": (
            "The ARM64 runtime binary (bin/kr_core) is not present in this package yet.\n\n"
            "Your config.json and input_config have been synced to:\n{data_dir}\n\n"
            "Build the full package via GitHub Actions CI (Phase 4: FEXCore + shadPS4 ARM64) "
            "to launch directly on an Android device."
        ),
    },
}


class KRAndroidLauncher:
    """Clean UI v1.0.0 (XSEmu-inspired) launcher for Android nixport & desktop testing."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app_dir = acfg.get_app_dir()
        self.data_dir = acfg.get_data_dir()
        self.patches_dir = acfg.get_patches_dir(self.app_dir)
        self.assets_dir = acfg.get_assets_dir(self.app_dir)
        self.on_device = acfg.is_nixport_device()
        self.scale = 1.25 if self.on_device else 1.0

        self.cfg = acfg.load_android_config(self.data_dir, self.app_dir)
        acfg.sync_android_engine_config(self.data_dir, self.cfg)

        self.active_tab = "play"
        self.trophy_filter = "all"
        self.patch_busy = False
        self.game_running = False
        self.selected_backup: str | None = None
        self.log_lines: list[str] = [
            f"[INIT] Kamen Rider: Memory of Heroes Android Port v{VERSION} Ready.",
            f"[STORAGE] Writable DATA_DIR: {self.data_dir}",
            f"[VULKAN] Async shader pipeline + mobile pool (1024MB DMEM / 512MB FMEM) synced.",
        ]
        if self.on_device:
            self.log_lines.append("[NIXPORT] FEXDROID_PRESENT active — fullscreen touch mode & mouse_to_joystick=none.")

        self._icon_small: tk.PhotoImage | None = None
        self._icon_poster: tk.PhotoImage | None = None
        self._load_icons()

        self._configure_window()
        self._build_ui()

    # ------------------------------------------------------------------ Helpers
    def _s(self, px: int) -> int:
        return max(1, int(round(px * self.scale)))

    def _font(self, size: int, bold: bool = False, mono: bool = False):
        family = "DejaVu Sans Mono" if mono else ("Segoe UI" if sys.platform == "win32" else "DejaVu Sans")
        weight = "bold" if bold else "normal"
        return (family, self._s(size), weight)

    def _t(self) -> dict:
        return THEMES.get(self.cfg.get("theme", "dark"), THEMES["dark"])

    def _tr(self, key: str, **kwargs) -> str:
        lang = self.cfg.get("language", "id")
        table = STRINGS.get(lang, STRINGS["id"])
        text = table.get(key, STRINGS["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def _load_icons(self) -> None:
        icon_path = self.assets_dir / "game_icon_rounded.png"
        if not icon_path.is_file():
            return
        try:
            raw = tk.PhotoImage(file=str(icon_path))
            w = max(1, raw.width())
            sub_small = max(1, round(w / self._s(28)))
            sub_poster = max(1, round(w / self._s(52)))
            self._icon_small = raw.subsample(sub_small, sub_small)
            self._icon_poster = raw.subsample(sub_poster, sub_poster)
        except Exception:
            self._icon_small = None
            self._icon_poster = None

    def _configure_window(self) -> None:
        self.root.title(f"Kamen Rider: Memory of Heroes — Android Port v{VERSION}")
        if self.on_device:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{sw}x{sh}+0+0")
            try:
                self.root.attributes("-fullscreen", True)
            except Exception:
                pass
        else:
            self.root.geometry("1060x660")
            self.root.minsize(920, 560)

    def _game_dir(self) -> Path | None:
        raw = self.cfg.get("game_dir", "").strip()
        return acfg.resolve_game_dir(raw) if raw else None

    def _game_meta(self) -> tuple[str, str]:
        gd = self._game_dir()
        if not gd:
            return ("CUSA17374", "01.00")
        info = sfo_parser.get_game_info(gd)
        return (info.get("TITLE_ID", "CUSA17374"), info.get("APP_VER", "01.00"))

    def _patch_status(self) -> dict:
        gd = self._game_dir() or Path("")
        return indo_patcher.get_indo_patch_status(gd, self.data_dir, self.patches_dir)

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self.log_lines.append(line)
        if len(self.log_lines) > 200:
            self.log_lines = self.log_lines[-200:]
        if hasattr(self, "log_widget") and self.log_widget.winfo_exists():
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", line + "\n")
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")

    def _save_and_sync(self, **updates) -> None:
        self.cfg.update({k: str(v) for k, v in updates.items()})
        self.cfg = acfg.save_android_config(self.data_dir, self.cfg)
        acfg.sync_android_engine_config(self.data_dir, self.cfg)

    # ------------------------------------------------------------------ UI Build
    def _build_ui(self) -> None:
        t = self._t()
        for child in self.root.winfo_children():
            child.destroy()

        self.root.configure(bg=t["bg_canvas"])

        shell = tk.Frame(self.root, bg=t["bg_canvas"])
        shell.pack(fill="both", expand=True)

        self._build_sidebar(shell)

        # Hairline vertical divider
        tk.Frame(shell, bg=t["border"], width=1).pack(side="left", fill="y")

        self.viewport = tk.Frame(shell, bg=t["bg_canvas"])
        self.viewport.pack(side="left", fill="both", expand=True)

        self._render_active_tab()

    def _build_sidebar(self, parent: tk.Frame) -> None:
        t = self._t()
        sb = tk.Frame(parent, bg=t["bg_sidebar"], width=self._s(210))
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Brand header
        brand = tk.Frame(sb, bg=t["bg_sidebar"])
        brand.pack(fill="x", padx=self._s(14), pady=(self._s(16), self._s(18)))
        if self._icon_small is not None:
            tk.Label(brand, image=self._icon_small, bg=t["bg_sidebar"], bd=0).pack(side="left", padx=(0, self._s(8)))
        tk.Label(
            brand,
            text="Memory of Heroes",
            bg=t["bg_sidebar"],
            fg=t["text_primary"],
            font=self._font(10, bold=True),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        # Navigation tabs
        patch_st = self._patch_status()
        nav_items = [
            ("play", self._tr("nav_play"), None),
            ("patch", self._tr("nav_patch"), "ID" if patch_st["applied"] else "EN"),
            ("saves", self._tr("nav_saves"), None),
            ("trophies", self._tr("nav_trophies"), None),
            ("settings", self._tr("nav_settings"), None),
        ]

        nav_wrap = tk.Frame(sb, bg=t["bg_sidebar"])
        nav_wrap.pack(fill="x", padx=self._s(10))

        for tab_id, label, badge in nav_items:
            is_active = self.active_tab == tab_id
            row_bg = t["bg_nav_active"] if is_active else t["bg_sidebar"]
            fg = t["text_primary"] if is_active else t["text_secondary"]

            row = tk.Frame(nav_wrap, bg=row_bg, cursor="hand2")
            row.pack(fill="x", pady=self._s(2))

            # Subtle left accent indicator when active
            ind = tk.Frame(row, bg=t["blue"] if is_active else row_bg, width=3)
            ind.pack(side="left", fill="y")

            lbl = tk.Label(
                row,
                text=label,
                bg=row_bg,
                fg=fg,
                font=self._font(10, bold=is_active),
                anchor="w",
                padx=self._s(10),
                pady=self._s(8),
            )
            lbl.pack(side="left", fill="x", expand=True)

            widgets = [row, ind, lbl]
            if badge is not None:
                b_bg = t["green_bg"] if badge == "ID" else t["bg_pill"]
                b_fg = t["green_text"] if badge == "ID" else t["text_muted"]
                b_lbl = tk.Label(
                    row,
                    text=badge,
                    bg=b_bg,
                    fg=b_fg,
                    font=self._font(8, bold=True),
                    padx=self._s(6),
                    pady=self._s(2),
                )
                b_lbl.pack(side="right", padx=(0, self._s(8)))
                widgets.append(b_lbl)

            for w in widgets:
                w.bind("<Button-1>", lambda _e, tid=tab_id: self._switch_tab(tid))

        # Spacer
        tk.Frame(sb, bg=t["bg_sidebar"]).pack(fill="both", expand=True)

        # Sidebar footer pills (FPS, Theme Dark/Light, Language ID/EN)
        tk.Frame(sb, bg=t["border"], height=1).pack(fill="x", padx=self._s(12), pady=(0, self._s(10)))
        foot = tk.Frame(sb, bg=t["bg_sidebar"])
        foot.pack(fill="x", padx=self._s(10), pady=(0, self._s(12)))

        fps_short = "30 FPS" if self.cfg["fps"].startswith("30") else "60 FPS"
        self._make_pill(foot, fps_short, fg=t["green_text"], bg=t["green_bg"]).pack(side="left", padx=(0, self._s(4)))

        theme_txt = self._tr("theme_dark") if self.cfg["theme"] == "dark" else self._tr("theme_light")
        self._make_pill(foot, theme_txt, cmd=self._toggle_theme).pack(side="left", padx=(0, self._s(4)))

        lang_txt = self.cfg["language"].upper()
        self._make_pill(foot, lang_txt, cmd=self._toggle_language).pack(side="left")

    def _make_pill(self, parent, text: str, fg=None, bg=None, cmd=None) -> tk.Label:
        t = self._t()
        lbl = tk.Label(
            parent,
            text=text,
            bg=bg or t["bg_pill"],
            fg=fg or t["text_secondary"],
            font=self._font(8, bold=True),
            padx=self._s(8),
            pady=self._s(4),
            cursor="hand2" if cmd else "",
            highlightthickness=1,
            highlightbackground=t["border"],
        )
        if cmd:
            lbl.bind("<Button-1>", lambda _e: cmd())
        return lbl

    def _make_button(self, parent, text: str, cmd, kind: str = "secondary", padx: int = 12, pady: int = 6) -> tk.Button:
        t = self._t()
        if kind == "primary":
            bg, fg, abg = t["blue"], "#FFFFFF", t["blue_hover"]
            bd_col = t["blue"]
        elif kind == "success":
            bg, fg, abg = t["green_bg"], t["green_text"], t["green_bg"]
            bd_col = t["green_dot"]
        elif kind == "danger":
            bg, fg, abg = t["red_bg"], t["red_text"], t["red_bg"]
            bd_col = t["red_text"]
        else:
            bg, fg, abg = t["bg_pill"], t["text_primary"], t["bg_hover"]
            bd_col = t["border_strong"]

        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=fg,
            activebackground=abg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=bd_col,
            font=self._font(9, bold=(kind == "primary")),
            padx=self._s(padx),
            pady=self._s(pady),
            cursor="hand2",
        )

    def _make_link_action(self, parent, text: str, cmd, danger: bool = False) -> tk.Label:
        t = self._t()
        lbl = tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg=t["red_text"] if danger else t["blue_text"],
            font=self._font(9, bold=True),
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda _e: cmd())
        return lbl

    def _make_card(self, parent) -> tk.Frame:
        t = self._t()
        return tk.Frame(
            parent,
            bg=t["bg_card"],
            highlightthickness=1,
            highlightbackground=t["border"],
            padx=self._s(14),
            pady=self._s(12),
        )

    def _make_segmented(self, parent, options: list[tuple[str, str]], current: str, on_select) -> tk.Frame:
        t = self._t()
        track = tk.Frame(
            parent,
            bg=t["bg_seg_track"],
            highlightthickness=1,
            highlightbackground=t["border"],
            padx=2,
            pady=2,
        )
        for val, label in options:
            active = val == current
            btn = tk.Label(
                track,
                text=label,
                bg=t["bg_seg_active"] if active else t["bg_seg_track"],
                fg=t["text_primary"] if active else t["text_secondary"],
                font=self._font(8, bold=active),
                padx=self._s(10),
                pady=self._s(4),
                cursor="hand2",
            )
            btn.pack(side="left", padx=1)
            btn.bind("<Button-1>", lambda _e, v=val: on_select(v))
        return track

    def _switch_tab(self, tab_id: str) -> None:
        self.active_tab = tab_id
        self._build_ui()

    def _render_active_tab(self) -> None:
        for child in self.viewport.winfo_children():
            child.destroy()

        if self.active_tab == "play":
            self._build_tab_overview()
        elif self.active_tab == "patch":
            self._build_tab_patch()
        elif self.active_tab == "saves":
            self._build_tab_saves()
        elif self.active_tab == "trophies":
            self._build_tab_trophies()
        elif self.active_tab == "settings":
            self._build_tab_settings()

    # ------------------------------------------------------------------ TAB 1: OVERVIEW
    def _build_tab_overview(self) -> None:
        t = self._t()
        title_id, app_ver = self._game_meta()
        gd = self._game_dir()
        patch_st = self._patch_status()

        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(14))

        # Hero banner card
        hero = self._make_card(wrap)
        hero.pack(fill="x", pady=(0, self._s(10)))

        tk.Label(
            hero,
            text=self._tr("hero_crumb"),
            bg=t["bg_card"],
            fg=t["text_muted"],
            font=self._font(8, bold=True),
            anchor="w",
        ).pack(fill="x", pady=(0, self._s(8)))

        hero_body = tk.Frame(hero, bg=t["bg_card"])
        hero_body.pack(fill="x")

        if self._icon_poster is not None:
            tk.Label(hero_body, image=self._icon_poster, bg=t["bg_card"], bd=0).pack(
                side="left", padx=(0, self._s(12))
            )

        htxt = tk.Frame(hero_body, bg=t["bg_card"])
        htxt.pack(side="left", fill="x", expand=True)
        tk.Label(
            htxt,
            text="Kamen Rider: Memory of Heroes",
            bg=t["bg_card"],
            fg=t["text_primary"],
            font=self._font(15, bold=True),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            htxt,
            text=self._tr("hero_sub", ver=app_ver),
            bg=t["bg_card"],
            fg=t["text_secondary"],
            font=self._font(9),
            anchor="w",
        ).pack(fill="x", pady=(self._s(2), 0))

        # Action bar
        bar = tk.Frame(wrap, bg=t["bg_canvas"])
        bar.pack(fill="x", pady=(0, self._s(10)))

        play_lbl = self._tr("btn_running") if self.game_running else self._tr("btn_play")
        self._make_button(bar, play_lbl, self._on_play, kind="primary", padx=20, pady=7).pack(
            side="left", padx=(0, self._s(8))
        )

        patch_btn_lbl = self._tr("patch_on") if patch_st["applied"] else self._tr("patch_off")
        patch_btn_kind = "success" if patch_st["applied"] else "secondary"
        self._make_button(
            bar,
            patch_btn_lbl,
            lambda: self._trigger_indo_patch(not patch_st["applied"]),
            kind=patch_btn_kind,
            padx=12,
            pady=7,
        ).pack(side="left", padx=(0, self._s(8)))

        if gd is not None:
            self._make_pill(bar, self._tr("badge_ready"), fg=t["green_text"], bg=t["green_bg"]).pack(side="left")
        else:
            self._make_pill(bar, self._tr("badge_missing"), fg=t["amber_text"], bg=t["amber_bg"]).pack(side="left")

        right_bar = tk.Frame(bar, bg=t["bg_canvas"])
        right_bar.pack(side="right")
        tk.Label(
            right_bar,
            text=self._tr("runs_with"),
            bg=t["bg_canvas"],
            fg=t["text_muted"],
            font=self._font(8),
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_pill(right_bar, "FEXCore + shadPS4 Vulkan 1.3", fg=t["text_primary"]).pack(side="left")

        # 2x2 Structured Spec Grid
        grid = tk.Frame(wrap, bg=t["bg_canvas"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1, uniform="col")
        grid.columnconfigure(1, weight=1, uniform="col")
        grid.rowconfigure(0, weight=1, uniform="row")
        grid.rowconfigure(1, weight=1, uniform="row")

        # Card 1: GAME
        c1 = self._make_card(grid)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, self._s(6)), pady=(0, self._s(6)))
        self._card_header(c1, self._tr("card_game"), self._tr("btn_verify"), self._on_verify_game)
        self._spec_row(c1, self._tr("lbl_version"), f"{app_ver} ({title_id})", mono=True)
        sub_txt = self._tr("sub_indo") if patch_st["applied"] else self._tr("sub_orig")
        self._spec_row(
            c1,
            self._tr("lbl_subtitle"),
            sub_txt,
            value_fg=t["green_text"] if patch_st["applied"] else t["text_primary"],
            action_text=self._tr("btn_switch"),
            action_cmd=lambda: self._trigger_indo_patch(not patch_st["applied"]),
        )
        self._spec_row(c1, self._tr("lbl_lead"), "AO Zero & Bakka Sub")
        gd_display = str(gd) if gd else self._tr("not_set")
        if len(gd_display) > 32:
            gd_display = "..." + gd_display[-29:]
        self._spec_row(
            c1,
            self._tr("lbl_folder"),
            gd_display,
            mono=True,
            action_text=self._tr("btn_change"),
            action_cmd=self._on_browse_game_dir,
        )

        # Card 2: SHADER CACHE & ENGINE
        c2 = self._make_card(grid)
        c2.grid(row=0, column=1, sticky="nsew", padx=(self._s(6), 0), pady=(0, self._s(6)))
        self._card_header(c2, self._tr("card_engine"), self._tr("btn_clear_cache"), self._on_clear_cache, danger=True)
        runtime_bin = acfg.find_runtime_binary(self.app_dir, self.data_dir)
        state_txt = "Ready · Async Pipelines" if runtime_bin else "Config Synced · Async Pipelines"
        self._spec_row(c2, self._tr("lbl_state"), state_txt, value_fg=t["green_text"])
        self._spec_row(c2, self._tr("lbl_render"), acfg.render_summary(self.cfg), mono=True)
        ctrl_txt = self._tr("ctrl_touch") if self.on_device else self._tr("ctrl_desktop")
        self._spec_row(c2, self._tr("lbl_controller"), ctrl_txt)
        slots_cnt = len(save_manager.get_save_slots(self.data_dir))
        self._spec_row(
            c2,
            self._tr("lbl_saves"),
            f"{slots_cnt} slot(s) · home/kr_moh",
            action_text=self._tr("btn_backup"),
            action_cmd=self._on_backup_saves,
        )

        # Card 3: ENGINE LOG
        c3 = self._make_card(grid)
        c3.grid(row=1, column=0, sticky="nsew", padx=(0, self._s(6)), pady=(self._s(6), 0))
        self._card_header(c3, self._tr("card_log"), self._tr("btn_clear"), self._on_clear_log, danger=True)
        self.log_widget = tk.Text(
            c3,
            bg=t["bg_input"],
            fg=t["text_secondary"],
            font=self._font(8, mono=True),
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=t["border"],
            wrap="word",
            height=6,
            padx=self._s(8),
            pady=self._s(6),
        )
        self.log_widget.pack(fill="both", expand=True, pady=(self._s(4), 0))
        self.log_widget.insert("1.0", "\n".join(self.log_lines) + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

        # Card 4: QUICK OVERRIDES
        c4 = self._make_card(grid)
        c4.grid(row=1, column=1, sticky="nsew", padx=(self._s(6), 0), pady=(self._s(6), 0))
        head4 = tk.Frame(c4, bg=t["bg_card"])
        head4.pack(fill="x", pady=(0, self._s(8)))
        tk.Label(
            head4, text=self._tr("card_overrides"), bg=t["bg_card"], fg=t["text_muted"], font=self._font(8, bold=True)
        ).pack(side="left")
        tk.Label(
            head4, text=self._tr("autosaved"), bg=t["bg_card"], fg=t["text_muted"], font=self._font(8)
        ).pack(side="right")

        self._override_row(
            c4,
            self._tr("lbl_resolution"),
            [
                ("540p (960x540)", "540p"),
                ("720p (1280x720)", "720p"),
                ("1080p (1920x1080)", "1080p"),
            ],
            self.cfg["resolution"],
            lambda v: self._set_quick_setting("resolution", v),
        )
        self._override_row(
            c4,
            self._tr("lbl_fps"),
            [
                ("30 FPS (Locked)", "30"),
                ("60 FPS (Native Unlock)", "60"),
            ],
            self.cfg["fps"],
            lambda v: self._set_quick_setting("fps", v),
        )
        self._override_row(
            c4,
            self._tr("lbl_fps_hud"),
            [("true", "On"), ("false", "Off")],
            self.cfg["show_fps"],
            lambda v: self._set_quick_setting("show_fps", v),
        )
        self._override_row(
            c4,
            self._tr("lbl_sub_id"),
            [("off", "Original"), ("on", "Bakka Sub")],
            "on" if patch_st["applied"] else "off",
            lambda v: self._trigger_indo_patch(v == "on"),
        )

    def _card_header(self, card: tk.Frame, title: str, action_text: str | None = None, action_cmd=None, danger: bool = False):
        t = self._t()
        head = tk.Frame(card, bg=t["bg_card"])
        head.pack(fill="x", pady=(0, self._s(8)))
        tk.Label(head, text=title, bg=t["bg_card"], fg=t["text_muted"], font=self._font(8, bold=True)).pack(side="left")
        if action_text and action_cmd:
            self._make_link_action(head, action_text, action_cmd, danger=danger).pack(side="right")

    def _spec_row(
        self,
        card: tk.Frame,
        label: str,
        value: str,
        mono: bool = False,
        value_fg: str | None = None,
        action_text: str | None = None,
        action_cmd=None,
    ) -> None:
        t = self._t()
        row = tk.Frame(card, bg=t["bg_card"])
        row.pack(fill="x", pady=self._s(3))
        tk.Label(
            row,
            text=label,
            bg=t["bg_card"],
            fg=t["text_secondary"],
            font=self._font(9),
            width=self._s(11),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            row,
            text=value,
            bg=t["bg_card"],
            fg=value_fg or t["text_primary"],
            font=self._font(9, mono=mono),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        if action_text and action_cmd:
            self._make_link_action(row, action_text, action_cmd).pack(side="right", padx=(self._s(6), 0))

    def _override_row(self, card: tk.Frame, label: str, options, current: str, on_select) -> None:
        t = self._t()
        row = tk.Frame(card, bg=t["bg_card"])
        row.pack(fill="x", pady=self._s(4))
        tk.Label(
            row,
            text=label,
            bg=t["bg_card"],
            fg=t["text_secondary"],
            font=self._font(9),
            width=self._s(12),
            anchor="w",
        ).pack(side="left")
        self._make_segmented(row, options, current, on_select).pack(side="right")

    # ------------------------------------------------------------------ TAB 2: PATCH INDO
    def _build_tab_patch(self) -> None:
        t = self._t()
        st = self._patch_status()

        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(16))

        tk.Label(
            wrap, text=self._tr("patch_title"), bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w"
        ).pack(fill="x")
        tk.Label(
            wrap, text=self._tr("patch_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w"
        ).pack(fill="x", pady=(self._s(2), self._s(14)))

        card = self._make_card(wrap)
        card.pack(fill="x")

        top = tk.Frame(card, bg=t["bg_card"])
        top.pack(fill="x", pady=(0, self._s(10)))
        self._make_pill(top, "ID", fg=t["blue_text"], bg=t["blue_soft"]).pack(side="left", padx=(0, self._s(8)))
        tk.Label(
            top,
            text=f"Bakka Sub x AO Zero · v{st['version']} · {st['translated_count']:,} strings",
            bg=t["bg_card"],
            fg=t["text_primary"],
            font=self._font(10, bold=True),
        ).pack(side="left")

        pill_txt = self._tr("sub_indo") if st["applied"] else self._tr("sub_orig")
        pill_fg = t["green_text"] if st["applied"] else t["text_secondary"]
        pill_bg = t["green_bg"] if st["applied"] else t["bg_pill"]
        self._make_pill(top, pill_txt, fg=pill_fg, bg=pill_bg).pack(side="right")

        meta_lines = [
            f"Patch Dictionary : {self.patches_dir / 'id_patch.json'} ({'OK' if st['patch_available'] else 'MISSING'})",
            f"Target Asset     : CUSA17374/Media/sharedassets0.assets ({'FOUND' if st['game_found'] else 'SELECT GAME FOLDER'})",
            f"Vanilla Backup   : {indo_patcher.get_backup_dir(self.data_dir)} ({'SAVED' if st['backup_exists'] else 'AUTO ON APPLY'})",
        ]
        tk.Label(
            card,
            text="\n".join(meta_lines),
            bg=t["bg_input"],
            fg=t["text_secondary"],
            font=self._font(8, mono=True),
            justify="left",
            anchor="w",
            padx=self._s(10),
            pady=self._s(8),
            highlightthickness=1,
            highlightbackground=t["border"],
        ).pack(fill="x", pady=(0, self._s(10)))

        tk.Label(
            card,
            text=self._tr("patch_note"),
            bg=t["bg_card"],
            fg=t["text_muted"],
            font=self._font(8),
            wraplength=self._s(740),
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, self._s(14)))

        btns = tk.Frame(card, bg=t["bg_card"])
        btns.pack(fill="x")
        if self.patch_busy:
            self._make_pill(btns, self._tr("patch_busy"), fg=t["amber_text"], bg=t["amber_bg"]).pack(side="left")
        else:
            self._make_button(
                btns, self._tr("btn_apply_indo"), lambda: self._trigger_indo_patch(True), kind="primary", padx=16, pady=8
            ).pack(side="left", padx=(0, self._s(8)))
            self._make_button(
                btns, self._tr("btn_restore_orig"), lambda: self._trigger_indo_patch(False), kind="secondary", padx=14, pady=8
            ).pack(side="left")

    # ------------------------------------------------------------------ TAB 3: SAVES
    def _build_tab_saves(self) -> None:
        t = self._t()
        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(16))

        head = tk.Frame(wrap, bg=t["bg_canvas"])
        head.pack(fill="x", pady=(0, self._s(12)))
        left = tk.Frame(head, bg=t["bg_canvas"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=self._tr("saves_title"), bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w").pack(fill="x")
        tk.Label(left, text=self._tr("saves_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w").pack(fill="x")
        self._make_button(head, self._tr("btn_backup_now"), self._on_backup_saves, kind="primary", padx=14, pady=7).pack(side="right")

        # Active slots card
        c_slots = self._make_card(wrap)
        c_slots.pack(fill="x", pady=(0, self._s(10)))
        self._card_header(c_slots, "ACTIVE SAVE SLOTS")
        slots = save_manager.get_save_slots(self.data_dir)
        if not slots:
            tk.Label(c_slots, text=self._tr("no_saves"), bg=t["bg_card"], fg=t["text_muted"], font=self._font(9), anchor="w").pack(fill="x")
        else:
            for sl in slots:
                self._spec_row(c_slots, sl["folder"], f"{sl['title']} · {sl['size_kb']} KB · {sl['last_modified']}")

        # Backups list card
        c_bak = self._make_card(wrap)
        c_bak.pack(fill="both", expand=True)
        self._card_header(c_bak, "BACKUP ARCHIVES (.ZIP)", self._tr("btn_restore_sel"), self._on_restore_selected)
        backups = save_manager.list_backups(self.data_dir)
        if not backups:
            tk.Label(c_bak, text=self._tr("no_backups"), bg=t["bg_card"], fg=t["text_muted"], font=self._font(9), anchor="w").pack(fill="x")
        else:
            lb = tk.Listbox(
                c_bak,
                bg=t["bg_input"],
                fg=t["text_primary"],
                selectbackground=t["blue"],
                selectforeground="#FFFFFF",
                font=self._font(9, mono=True),
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=t["border"],
            )
            lb.pack(fill="both", expand=True, pady=(self._s(4), 0))
            self._backup_names = [b["name"] for b in backups]
            for b in backups:
                lb.insert("end", f"{b['name']}   ({b['size_kb']} KB · {b['date']})")
            lb.bind("<<ListboxSelect>>", lambda e: self._on_select_backup(e.widget))
            if self._backup_names:
                lb.selection_set(0)
                self.selected_backup = self._backup_names[0]

    # ------------------------------------------------------------------ TAB 4: TROPHIES
    def _build_tab_trophies(self) -> None:
        t = self._t()
        lang = self.cfg.get("language", "id")
        all_tr = trophy_manager.load_trophies(self.data_dir)
        unlocked_cnt = sum(1 for item in all_tr if item["unlocked"])

        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(16))

        head = tk.Frame(wrap, bg=t["bg_canvas"])
        head.pack(fill="x", pady=(0, self._s(10)))
        left = tk.Frame(head, bg=t["bg_canvas"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=f"{self._tr('trophies_title')} ({unlocked_cnt}/{len(all_tr)})", bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w").pack(fill="x")
        tk.Label(left, text=self._tr("trophies_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w").pack(fill="x")

        self._make_segmented(
            head,
            [("all", self._tr("filter_all")), ("unlocked", self._tr("filter_unlocked")), ("locked", self._tr("filter_locked"))],
            self.trophy_filter,
            self._set_trophy_filter,
        ).pack(side="right")

        filtered = [
            item for item in all_tr
            if self.trophy_filter == "all"
            or (self.trophy_filter == "unlocked" and item["unlocked"])
            or (self.trophy_filter == "locked" and not item["unlocked"])
        ]

        # Scrollable canvas list
        outer = self._make_card(wrap)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=t["bg_card"], highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=t["bg_card"])
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for item in filtered:
            tier = item["type"]
            tier_fg = t.get(tier, t["text_secondary"])
            name = item["name_id"] if lang == "id" else item["name_en"]
            desc = item["desc_id"] if lang == "id" else item["desc_en"]

            row = tk.Frame(inner, bg=t["bg_card"], pady=self._s(6))
            row.pack(fill="x", padx=self._s(4))
            self._make_pill(row, tier.upper()[:4], fg=tier_fg, bg=t["bg_pill"]).pack(side="left", padx=(0, self._s(10)))
            info = tk.Frame(row, bg=t["bg_card"])
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=name, bg=t["bg_card"], fg=t["text_primary"], font=self._font(9, bold=True), anchor="w").pack(fill="x")
            tk.Label(info, text=desc, bg=t["bg_card"], fg=t["text_secondary"], font=self._font(8), anchor="w").pack(fill="x")
            st_lbl = "UNLOCKED" if item["unlocked"] else "LOCKED"
            self._make_pill(
                row,
                st_lbl,
                fg=t["green_text"] if item["unlocked"] else t["text_muted"],
                bg=t["green_bg"] if item["unlocked"] else t["bg_pill"],
            ).pack(side="right", padx=(self._s(10), 0))
            tk.Frame(inner, bg=t["border"], height=1).pack(fill="x")

    # ------------------------------------------------------------------ TAB 5: SETTINGS
    def _build_tab_settings(self) -> None:
        t = self._t()
        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(16))

        tk.Label(wrap, text=self._tr("settings_title"), bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w").pack(fill="x")
        tk.Label(wrap, text=self._tr("settings_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w").pack(fill="x", pady=(self._s(2), self._s(12)))

        c_gfx = self._make_card(wrap)
        c_gfx.pack(fill="x", pady=(0, self._s(10)))
        self._card_header(c_gfx, self._tr("sec_graphics"))
        self._override_row(
            c_gfx,
            self._tr("lbl_fsr"),
            [("true", "On"), ("false", "Off")],
            self.cfg["fsr_enabled"],
            lambda v: self._set_quick_setting("fsr_enabled", v),
        )
        self._override_row(
            c_gfx,
            self._tr("lbl_async"),
            [("true", "On"), ("false", "Off")],
            self.cfg["async_shaders"],
            lambda v: self._set_quick_setting("async_shaders", v),
        )
        self._override_row(
            c_gfx,
            self._tr("lbl_vsync"),
            [(v, v) for v in acfg.VSYNC_OPTIONS],
            self.cfg["vsync_mode"],
            lambda v: self._set_quick_setting("vsync_mode", v),
        )
        self._override_row(
            c_gfx,
            self._tr("lbl_backend"),
            [("auto", "Auto"), ("x11", "X11"), ("wayland", "Wayland")],
            self.cfg["video_backend"],
            lambda v: self._set_quick_setting("video_backend", v),
        )

        c_sys = self._make_card(wrap)
        c_sys.pack(fill="x", pady=(0, self._s(10)))
        self._card_header(c_sys, self._tr("sec_system"))
        self._override_row(
            c_sys,
            self._tr("lbl_theme"),
            [("dark", self._tr("theme_dark")), ("light", self._tr("theme_light"))],
            self.cfg["theme"],
            lambda v: self._set_quick_setting("theme", v),
        )
        self._override_row(
            c_sys,
            self._tr("lbl_lang"),
            [("id", "Bahasa Indonesia"), ("en", "English")],
            self.cfg["language"],
            lambda v: self._set_quick_setting("language", v),
        )
        self._spec_row(c_sys, "DATA_DIR", str(self.data_dir), mono=True)
        self._spec_row(c_sys, "APP_DIR", str(self.app_dir), mono=True)

        c_cred = self._make_card(wrap)
        c_cred.pack(fill="x")
        self._card_header(c_cred, self._tr("sec_credits"))
        self._spec_row(c_cred, "Port Lead", "AO Zero · Community Partner: Bakka Sub (www.bakkasub.my.id)")
        self._spec_row(c_cred, "Architecture", "nixport + FEXCore + shadPS4 Vulkan 1.3 · Clean UI inspired by XSEmu (GPL-2.0)")

    # ------------------------------------------------------------------ Actions
    def _set_quick_setting(self, key: str, value: str) -> None:
        self._save_and_sync(**{key: value})
        self._append_log(f"[CONFIG] {key} = {value} (synced to config.json)")
        self._build_ui()

    def _toggle_theme(self) -> None:
        nxt = "light" if self.cfg.get("theme", "dark") == "dark" else "dark"
        self._set_quick_setting("theme", nxt)

    def _toggle_language(self) -> None:
        nxt = "en" if self.cfg.get("language", "id") == "id" else "id"
        self._set_quick_setting("language", nxt)

    def _set_trophy_filter(self, val: str) -> None:
        self.trophy_filter = val
        self._render_active_tab()

    def _on_clear_log(self) -> None:
        self.log_lines = []
        if hasattr(self, "log_widget") and self.log_widget.winfo_exists():
            self.log_widget.configure(state="normal")
            self.log_widget.delete("1.0", "end")
            self.log_widget.configure(state="disabled")

    def _on_browse_game_dir(self) -> None:
        initial = self.cfg.get("game_dir") or ("/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else str(self.data_dir))
        chosen = filedialog.askdirectory(title="Select CUSA17374 Game Folder", initialdir=initial)
        if not chosen:
            return
        resolved = acfg.resolve_game_dir(chosen)
        if resolved is None:
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return
        self._save_and_sync(game_dir=str(resolved))
        self._append_log(f"[GAME] Selected CUSA17374 directory: {resolved}")
        self._build_ui()

    def _on_verify_game(self) -> None:
        gd = self._game_dir()
        if gd is None:
            self._append_log("[VERIFY] Game folder not set or eboot.bin missing.")
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return
        assets_ok = (gd / "Media" / "sharedassets0.assets").is_file()
        sfo_ok = (gd / "sce_sys" / "param.sfo").is_file()
        title_id, app_ver = self._game_meta()
        msg = f"[VERIFY] OK — {title_id} v{app_ver} | eboot.bin: OK | param.sfo: {'OK' if sfo_ok else 'MISSING'} | sharedassets0.assets: {'OK' if assets_ok else 'MISSING'}"
        self._append_log(msg)

    def _on_clear_cache(self) -> None:
        res = acfg.clear_shader_cache(self.data_dir)
        self._append_log(f"[CACHE] Cleared {res['removed_files']} file(s), freed {res['freed_mb']} MB.")

    def _on_backup_saves(self) -> None:
        res = save_manager.backup_saves(self.data_dir)
        self._append_log(f"[SAVE] {res['message']}")
        if self.active_tab == "saves":
            self._render_active_tab()

    def _on_select_backup(self, listbox: tk.Listbox) -> None:
        sel = listbox.curselection()
        if sel and hasattr(self, "_backup_names"):
            self.selected_backup = self._backup_names[sel[0]]

    def _on_restore_selected(self) -> None:
        if not self.selected_backup:
            return
        res = save_manager.restore_backup(self.data_dir, self.selected_backup)
        self._append_log(f"[SAVE] {res['message']}")
        self._render_active_tab()

    def _trigger_indo_patch(self, enable: bool) -> None:
        if self.patch_busy:
            return
        gd = self._game_dir()
        if gd is None:
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return

        self.patch_busy = True
        self._build_ui()

        def worker() -> None:
            def cb(msg: str) -> None:
                self.root.after(0, lambda m=msg: self._append_log(m))

            try:
                if enable:
                    res = indo_patcher.apply_indo_patch(gd, self.data_dir, self.patches_dir, progress_cb=cb)
                else:
                    res = indo_patcher.restore_vanilla(gd, self.data_dir, progress_cb=cb)
                applied = bool(res.get("applied", False))
                self._save_and_sync(indo_patch="true" if applied else "false")
                self.root.after(0, lambda r=res: self._finish_patch(r))
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._finish_patch({"success": False, "message": str(e)}))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_patch(self, res: dict) -> None:
        self.patch_busy = False
        self._append_log(f"[PATCH-ID] {res.get('message', '')}")
        self._build_ui()

    def _on_play(self) -> None:
        if self.game_running:
            return
        gd = self._game_dir()
        if gd is None:
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return

        acfg.sync_android_engine_config(self.data_dir, self.cfg)
        runtime_bin = acfg.find_runtime_binary(self.app_dir, self.data_dir)
        if runtime_bin is None:
            self._append_log("[LAUNCH] ARM64 runtime binary (bin/kr_core) not bundled yet — config synced.")
            messagebox.showinfo(
                self._tr("err_no_runtime_title"),
                self._tr("err_no_runtime_msg", data_dir=str(self.data_dir)),
            )
            return

        eboot = gd / "eboot.bin"
        cmd = [str(runtime_bin), "-g", str(eboot.resolve()), "-f", "true"]
        if self.cfg.get("show_fps") == "true":
            cmd.append("--show-fps")

        env = dict(os.environ)
        env["HOME"] = str(self.data_dir.parent)
        env["XDG_DATA_HOME"] = str(self.data_dir / "bin" / "user")
        if self.cfg.get("video_backend", "auto") != "auto":
            env["SDL_VIDEODRIVER"] = self.cfg["video_backend"]

        log_path = acfg.get_log_dir(self.data_dir) / "launch.log"
        self._append_log(f"[LAUNCH] Executing: {' '.join(cmd)}")
        self.game_running = True
        self._build_ui()

        def run_proc() -> None:
            rc = -1
            try:
                with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
                    lf.write(f"=== Kamen Rider: Memory of Heroes Launch ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    lf.write(f"CMD: {' '.join(cmd)}\n\n")
                    lf.flush()
                    proc = subprocess.Popen(cmd, cwd=str(self.data_dir), env=env, stdout=lf, stderr=subprocess.STDOUT)
                    rc = proc.wait()
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._append_log(f"[LAUNCH ERROR] {e}"))
            finally:
                self.root.after(0, lambda code=rc: self._on_game_exit(code))

        threading.Thread(target=run_proc, daemon=True).start()

    def _on_game_exit(self, rc: int) -> None:
        self.game_running = False
        self._append_log(f"[LAUNCH] Game session exited (code {rc}).")
        self._build_ui()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kamen Rider: Memory of Heroes Android ARM64 Launcher")
    parser.add_argument("--smoke-test", action="store_true", help="Initialize UI, render all tabs, and exit cleanly.")
    args = parser.parse_args(argv)

    root = tk.Tk()
    app = KRAndroidLauncher(root)
    if args.smoke_test:
        for tab in ("play", "patch", "saves", "trophies", "settings"):
            app._switch_tab(tab)
            root.update_idletasks()
        app._toggle_theme()
        root.update_idletasks()
        root.destroy()
        print("[SMOKE-TEST] Clean UI v1.0.0 launcher initialized & rendered all 5 tabs + Dark/Light theme OK.")
        return 0

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
