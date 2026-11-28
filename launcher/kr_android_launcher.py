#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
================================================================================
  KAMEN RIDER: MEMORY OF HEROES (CUSA17374) | ANDROID ARM64 LAUNCHER (v1.0.0)
  Design: Clean Desktop / Mobile-Adaptive UI (Dark & Light Mode, XSEmu-inspired)
  Port Lead: AO Zero | Community Partner: Bakka Sub (https://www.bakkasub.my.id)
================================================================================
Pure Python stdlib (tkinter) with zero external dependencies. Runs natively inside
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
import android_diagnostics as adiag  # noqa: E402
import android_i18n as ai18n  # noqa: E402
import android_updater as aupd  # noqa: E402
import indo_patcher  # noqa: E402
import save_manager  # noqa: E402
import session_tracker  # noqa: E402
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


class KRAndroidLauncher:
    """Clean UI v1.0.0 (XSEmu-inspired) launcher for Android nixport & desktop testing."""

    def __init__(self, root: tk.Tk, skip_network: bool = False) -> None:
        self.root = root
        self.app_dir = acfg.get_app_dir()
        self.data_dir = acfg.get_data_dir()
        self.patches_dir = acfg.get_patches_dir(self.app_dir)
        self.assets_dir = acfg.get_assets_dir(self.app_dir)
        self.on_device = acfg.is_nixport_device()
        self.scale = self._compute_scale()
        self._active_wheel_canvas: tk.Canvas | None = None
        self._patch_progress_text = ""

        self.cfg = acfg.load_android_config(self.data_dir, self.app_dir)
        acfg.sync_android_engine_config(self.data_dir, self.cfg)
        self.hw_info = adiag.detect_device_hardware(self.data_dir)

        self.active_tab = "play"
        self.trophy_filter = "all"
        self.patch_busy = False
        self.game_running = False
        self.update_busy = False
        self.update_info: dict | None = None
        self.selected_backup: str | None = None

        self.log_lines: list[str] = [
            f"[INIT] Kamen Rider: Memory of Heroes Android Port v{VERSION} Ready.",
            f"[STORAGE] Writable DATA_DIR: {self.data_dir}",
            f"[DEVICE] {self.hw_info['device']} | {self.hw_info['soc']} | {self.hw_info['ram_gb']} GB RAM",
        ]
        if self.on_device:
            self.log_lines.append("[NIXPORT] FEXDROID_PRESENT active: fullscreen touch mode & mouse_to_joystick=none.")

        self._icon_small: tk.PhotoImage | None = None
        self._icon_poster: tk.PhotoImage | None = None
        self._load_icons()

        self._configure_window()
        self._build_ui()

        if not skip_network and self.cfg.get("check_updates_startup", "true") == "true":
            self._check_updates_async(silent=True)

    # ------------------------------------------------------------------ Helpers
    def _compute_scale(self) -> float:
        if not self.on_device:
            return 1.0
        sh = max(480, self.root.winfo_screenheight())
        if sh <= 600:
            return 0.78
        if sh <= 800:
            return 1.0
        if sh <= 1150:
            return 1.12
        return 1.22

    def _s(self, px: int) -> int:
        return max(1, int(round(px * self.scale)))

    def _make_scroll_area(self, parent: tk.Frame, bg: str) -> tuple[tk.Canvas, tk.Frame]:
        """Reusable full-width scrollable container with global mousewheel support."""
        canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, bd=0, width=1, height=1)
        sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=bg)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._bind_wheel_canvas(canvas)
        return canvas, inner

    def _bind_wheel_canvas(self, canvas: tk.Canvas) -> None:
        self._active_wheel_canvas = canvas

        def _on_wheel(ev):
            c = self._active_wheel_canvas
            if c is None or not c.winfo_exists():
                return
            if ev.num == 4:
                c.yview_scroll(-3, "units")
            elif ev.num == 5:
                c.yview_scroll(3, "units")
            elif getattr(ev, "delta", 0):
                c.yview_scroll(-1 if ev.delta > 0 else 1, "units")

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(seq, _on_wheel)

    def _unbind_wheel_canvas(self) -> None:
        self._active_wheel_canvas = None
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.unbind_all(seq)

    def _font(self, size: int, bold: bool = False, mono: bool = False):
        family = "DejaVu Sans Mono" if mono else ("Segoe UI" if sys.platform == "win32" else "DejaVu Sans")
        weight = "bold" if bold else "normal"
        return (family, self._s(size), weight)

    def _t(self) -> dict:
        return THEMES.get(self.cfg.get("theme", "dark"), THEMES["dark"])

    def _tr(self, key: str, **kwargs) -> str:
        return ai18n.tr(self.cfg.get("language", "id"), key, **kwargs)

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
        self.root.title(f"Kamen Rider: Memory of Heroes (Android Port v{VERSION})")
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
        gd = self._game_dir()
        target = gd if gd is not None else (self.data_dir / "__unset_game_dir__")
        return indo_patcher.get_indo_patch_status(target, self.data_dir, self.patches_dir)

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
        self._unbind_wheel_canvas()
        for child in self.root.winfo_children():
            child.destroy()

        self.root.configure(bg=t["bg_canvas"])

        shell = tk.Frame(self.root, bg=t["bg_canvas"])
        shell.pack(fill="both", expand=True)

        self._build_sidebar(shell)
        tk.Frame(shell, bg=t["border"], width=1).pack(side="left", fill="y")

        self.viewport = tk.Frame(shell, bg=t["bg_canvas"])
        self.viewport.pack(side="left", fill="both", expand=True)

        self._render_active_tab()

    def _build_sidebar(self, parent: tk.Frame) -> None:
        t = self._t()
        sb = tk.Frame(parent, bg=t["bg_sidebar"], width=self._s(210))
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

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

        tk.Frame(sb, bg=t["bg_sidebar"]).pack(fill="both", expand=True)

        tk.Frame(sb, bg=t["border"], height=1).pack(fill="x", padx=self._s(12), pady=(0, self._s(10)))
        foot = tk.Frame(sb, bg=t["bg_sidebar"])
        foot.pack(fill="x", padx=self._s(10), pady=(0, self._s(12)))

        fps_short = "30 FPS" if self.cfg["fps"].startswith("30") else "60 FPS"
        self._make_pill(foot, fps_short, fg=t["green_text"], bg=t["green_bg"]).pack(side="left", padx=(0, self._s(4)))

        theme_txt = self._tr("theme_dark") if self.cfg["theme"] == "dark" else self._tr("theme_light")
        self._make_pill(foot, theme_txt, cmd=self._toggle_theme).pack(side="left", padx=(0, self._s(4)))

        lang_code = ai18n.normalize_lang(self.cfg.get("language", "id"))
        self._make_pill(foot, ai18n.LANG_SHORT[lang_code], cmd=self._cycle_language).pack(side="left")

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
                padx=self._s(9),
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
        self._unbind_wheel_canvas()
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
        stats = session_tracker.get_formatted_stats(self.data_dir)
        cache_st = adiag.get_shader_cache_stats(self.data_dir)

        wrap = tk.Frame(self.viewport, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(14))

        # Hero banner card
        hero = self._make_card(wrap)
        hero.pack(fill="x", pady=(0, self._s(10)))

        top_crumb = tk.Frame(hero, bg=t["bg_card"])
        top_crumb.pack(fill="x", pady=(0, self._s(6)))
        tk.Label(
            top_crumb,
            text=self._tr("hero_crumb"),
            bg=t["bg_card"],
            fg=t["text_muted"],
            font=self._font(8, bold=True),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            top_crumb,
            text=f"{stats['playtime_text']} · {stats['last_played_text']}",
            bg=t["bg_card"],
            fg=t["text_secondary"],
            font=self._font(8, mono=True),
            anchor="e",
        ).pack(side="right")

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
        self._make_button(bar, play_lbl, self._on_play, kind="primary", padx=18, pady=7).pack(
            side="left", padx=(0, self._s(8))
        )

        if self.patch_busy:
            patch_btn_lbl = self._tr("patch_busy")
            patch_btn_kind = "secondary"
        else:
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

        if self.update_info and not self.update_info.get("up_to_date", True):
            upd_tag = self.update_info.get("latest", "")
            self._make_pill(
                bar,
                f"Update {upd_tag}",
                fg=t["blue_text"],
                bg=t["blue_soft"],
                cmd=lambda: self._switch_tab("settings"),
            ).pack(side="left", padx=(self._s(6), 0))

        right_bar = tk.Frame(bar, bg=t["bg_canvas"])
        right_bar.pack(side="right")
        tk.Label(
            right_bar,
            text=self._tr("runs_with"),
            bg=t["bg_canvas"],
            fg=t["text_muted"],
            font=self._font(8),
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_pill(right_bar, "FEXCore + shadPS4", fg=t["text_primary"]).pack(side="left")

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
        if len(gd_display) > 28:
            gd_display = "..." + gd_display[-25:]
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
        self._spec_row(c2, self._tr("lbl_shaders"), cache_st["summary"], value_fg=t["green_text"], mono=True)
        self._spec_row(c2, self._tr("lbl_render"), acfg.render_summary(self.cfg), mono=True)
        ctrl_txt = self._tr("ctrl_touch") if self.on_device else self._tr("ctrl_desktop")
        self._spec_row(c2, self._tr("lbl_controller"), ctrl_txt)
        self._spec_row(
            c2,
            self._tr("lbl_last_run"),
            stats["last_result"],
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
            width=1,
            height=4,
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
            width=self._s(13),
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

        def _short_path(p: Path, maxlen: int = 44) -> str:
            s = str(p)
            return ("..." + s[-(maxlen - 3):]) if len(s) > maxlen else s

        meta_lines = [
            f"Patch Dictionary : {_short_path(self.patches_dir / 'id_patch.json')} ({'OK' if st['patch_available'] else 'MISSING'})",
            f"Target Asset     : CUSA17374/Media/sharedassets0.assets ({'FOUND' if st['game_found'] else 'SELECT GAME FOLDER'})",
            f"Vanilla Backup   : {_short_path(indo_patcher.get_backup_dir(self.data_dir))} ({'SAVED' if st['backup_exists'] else 'AUTO ON APPLY'})",
        ]
        tk.Label(
            card,
            text="\n".join(meta_lines),
            bg=t["bg_input"],
            fg=t["text_secondary"],
            font=self._font(8, mono=True),
            justify="left",
            anchor="w",
            wraplength=self._s(600),
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
            wraplength=self._s(600),
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, self._s(12)))

        if self._patch_progress_text:
            self.patch_progress_lbl = tk.Label(
                card,
                text=self._patch_progress_text,
                bg=t["bg_card"],
                fg=t["amber_text"] if self.patch_busy else t["green_text"],
                font=self._font(8, mono=True),
                wraplength=self._s(600),
                justify="left",
                anchor="w",
            )
            self.patch_progress_lbl.pack(fill="x", pady=(0, self._s(10)))

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
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(14))

        head = tk.Frame(wrap, bg=t["bg_canvas"])
        head.pack(fill="x", pady=(0, self._s(10)))
        left = tk.Frame(head, bg=t["bg_canvas"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=self._tr("saves_title"), bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w").pack(fill="x")
        tk.Label(left, text=self._tr("saves_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w").pack(fill="x")

        actions = tk.Frame(head, bg=t["bg_canvas"])
        actions.pack(side="right")
        self._make_button(actions, self._tr("btn_import_save"), self._on_import_save_zip, kind="secondary", padx=10, pady=6).pack(
            side="left", padx=(0, self._s(6))
        )
        self._make_button(actions, self._tr("btn_backup_now"), self._on_backup_saves, kind="primary", padx=12, pady=6).pack(
            side="left"
        )

        # Auto-backup toggle strip
        c_opt = self._make_card(wrap)
        c_opt.pack(fill="x", pady=(0, self._s(8)))
        self._override_row(
            c_opt,
            self._tr("lbl_auto_backup"),
            [("true", "On"), ("false", "Off")],
            self.cfg.get("auto_backup_saves", "true"),
            lambda v: self._set_quick_setting("auto_backup_saves", v),
        )

        # Active slots card
        c_slots = self._make_card(wrap)
        c_slots.pack(fill="x", pady=(0, self._s(8)))
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
        lang = ai18n.normalize_lang(self.cfg.get("language", "id"))
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

        outer = self._make_card(wrap)
        outer.pack(fill="both", expand=True)
        _canvas, inner = self._make_scroll_area(outer, t["bg_card"])

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
        cache_st = adiag.get_shader_cache_stats(self.data_dir)
        scroll_host = tk.Frame(self.viewport, bg=t["bg_canvas"])
        scroll_host.pack(fill="both", expand=True)
        _canvas, sc_inner = self._make_scroll_area(scroll_host, t["bg_canvas"])

        wrap = tk.Frame(sc_inner, bg=t["bg_canvas"])
        wrap.pack(fill="both", expand=True, padx=self._s(18), pady=self._s(14))

        tk.Label(wrap, text=self._tr("settings_title"), bg=t["bg_canvas"], fg=t["text_primary"], font=self._font(14, bold=True), anchor="w").pack(fill="x")
        tk.Label(wrap, text=self._tr("settings_sub"), bg=t["bg_canvas"], fg=t["text_secondary"], font=self._font(9), anchor="w").pack(fill="x", pady=(self._s(2), self._s(12)))

        # Card 1: 1-Click Mobile Presets
        c_pre = self._make_card(wrap)
        c_pre.pack(fill="x", pady=(0, self._s(10)))
        self._card_header(c_pre, self._tr("sec_presets"))
        pre_row = tk.Frame(c_pre, bg=t["bg_card"])
        pre_row.pack(fill="x")
        self._make_button(pre_row, self._tr("btn_preset_auto"), self._on_apply_auto_preset, kind="primary", padx=12, pady=6).pack(
            side="left", padx=(0, self._s(6))
        )
        self._make_button(
            pre_row,
            self._tr("btn_preset_540"),
            lambda: self._apply_preset("540p (960x540)", "30 FPS (Locked)", "true"),
            kind="secondary",
            padx=10,
            pady=6,
        ).pack(side="left", padx=(0, self._s(6)))
        self._make_button(
            pre_row,
            self._tr("btn_preset_720"),
            lambda: self._apply_preset("720p (1280x720)", "60 FPS (Native Unlock)", "true"),
            kind="secondary",
            padx=10,
            pady=6,
        ).pack(side="left")

        # Card 2: Graphics, Audio & Controls
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
        self._override_row(
            c_gfx,
            self._tr("lbl_volume"),
            [("0", "Mute"), ("25", "25%"), ("50", "50%"), ("75", "75%"), ("100", "100%")],
            self.cfg["audio_volume"],
            lambda v: self._set_quick_setting("audio_volume", v),
        )
        self._override_row(
            c_gfx,
            self._tr("lbl_deadzone"),
            [("5", "5%"), ("8", "8%"), ("12", "12%"), ("15", "15%"), ("20", "20%")],
            self.cfg["deadzone"],
            lambda v: self._set_quick_setting("deadzone", v),
        )

        # Card 3: System, Theme & 5-Language Switcher
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
            [(code, ai18n.LANG_SHORT[code]) for code in ai18n.SUPPORTED_LANGS],
            ai18n.normalize_lang(self.cfg["language"]),
            lambda v: self._set_quick_setting("language", v),
        )
        self._override_row(
            c_sys,
            self._tr("lbl_update_startup"),
            [("true", "On"), ("false", "Off")],
            self.cfg.get("check_updates_startup", "true"),
            lambda v: self._set_quick_setting("check_updates_startup", v),
        )
        self._spec_row(c_sys, "DATA_DIR", str(self.data_dir), mono=True)
        sys_btns = tk.Frame(c_sys, bg=t["bg_card"])
        sys_btns.pack(fill="x", pady=(self._s(8), 0))
        self._make_button(sys_btns, self._tr("btn_clean_temp"), self._on_clean_temp, kind="secondary", padx=10, pady=5).pack(
            side="left", padx=(0, self._s(6))
        )
        self._make_button(sys_btns, self._tr("btn_reset_all"), self._on_reset_defaults, kind="danger", padx=10, pady=5).pack(
            side="left"
        )

        # Card 4: Device Specs, Diagnostics & Update Checker
        c_diag = self._make_card(wrap)
        c_diag.pack(fill="x", pady=(0, self._s(10)))
        self._card_header(c_diag, self._tr("sec_specs"), self._tr("btn_copy_specs"), self._on_copy_specs)
        self._spec_row(c_diag, "Device", f"{self.hw_info['device']} ({self.hw_info['arch']})")
        self._spec_row(c_diag, "SoC / CPU", self.hw_info["soc"])
        self._spec_row(c_diag, "RAM / Disk", f"{self.hw_info['ram_gb']} GB RAM · {self.hw_info['disk_free']}", mono=True)
        self._spec_row(c_diag, "Vulkan ICD", self.hw_info["vulkan_summary"])
        self._spec_row(c_diag, "Shader Cache", cache_st["summary"], mono=True)
        self._spec_row(c_diag, "Recommended", self.hw_info["recommended"], value_fg=t["green_text"])
        if self.update_info:
            upd_col = t["blue_text"] if not self.update_info.get("up_to_date", True) else t["text_secondary"]
            self._spec_row(c_diag, "Update", self.update_info.get("message", ""), value_fg=upd_col)

        diag_btns = tk.Frame(c_diag, bg=t["bg_card"])
        diag_btns.pack(fill="x", pady=(self._s(8), 0))
        self._make_button(diag_btns, self._tr("btn_export_diag"), self._on_export_diagnostic, kind="primary", padx=12, pady=6).pack(
            side="left", padx=(0, self._s(6))
        )
        self._make_button(
            diag_btns,
            self._tr("btn_check_update"),
            lambda: self._check_updates_async(silent=False),
            kind="secondary",
            padx=10,
            pady=6,
        ).pack(side="left", padx=(0, self._s(6)))
        if self.update_info and self.update_info.get("download_url") and not self.update_info.get("up_to_date", True):
            self._make_button(
                diag_btns,
                self._tr("btn_download_update"),
                self._on_download_update,
                kind="success",
                padx=10,
                pady=6,
            ).pack(side="left")

        # Card 5: Credits
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

    def _apply_preset(self, resolution: str, fps: str, fsr: str) -> None:
        self._save_and_sync(resolution=resolution, fps=fps, fsr_enabled=fsr, async_shaders="true")
        self._append_log(f"[PRESET] Applied {resolution} / {fps} / FSR={fsr}")
        self._build_ui()

    def _on_apply_auto_preset(self) -> None:
        p = self.hw_info.get("recommended_preset") or adiag.recommend_mobile_preset(self.hw_info)
        self._apply_preset(p["resolution"], p["fps"], p["fsr_enabled"])

    def _toggle_theme(self) -> None:
        nxt = "light" if self.cfg.get("theme", "dark") == "dark" else "dark"
        self._set_quick_setting("theme", nxt)

    def _cycle_language(self) -> None:
        nxt = ai18n.next_lang(self.cfg.get("language", "id"))
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
        msg = f"[VERIFY] OK: {title_id} v{app_ver} | eboot.bin: OK | param.sfo: {'OK' if sfo_ok else 'MISSING'} | sharedassets0.assets: {'OK' if assets_ok else 'MISSING'}"
        self._append_log(msg)

    def _on_clear_cache(self) -> None:
        res = acfg.clear_shader_cache(self.data_dir)
        self._append_log(f"[CACHE] Cleared {res['removed_files']} file(s), freed {res['freed_mb']} MB.")
        self._build_ui()

    def _on_clean_temp(self) -> None:
        res = acfg.clean_temp_files(self.data_dir)
        self._append_log(f"[TEMP] Removed {res['removed']} temporary file(s).")
        messagebox.showinfo("Clean Temp", f"Removed {res['removed']} temporary file(s).")

    def _on_reset_defaults(self) -> None:
        if not messagebox.askyesno("Reset Defaults", "Reset all launcher graphics, audio, and UI settings to mobile defaults?"):
            return
        self.cfg = acfg.reset_to_defaults(self.data_dir, keep_game_dir=True)
        self._append_log("[CONFIG] Restored factory mobile defaults.")
        self._build_ui()

    def _on_copy_specs(self) -> None:
        cache_st = adiag.get_shader_cache_stats(self.data_dir)
        txt = adiag.format_specs_clipboard(self.hw_info, VERSION, cache_st)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self._append_log("[SPECS] Copied device specs to clipboard.")
        except Exception as exc:
            self._append_log(f"[SPECS] Clipboard unavailable: {exc}")

    def _on_export_diagnostic(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = adiag.default_diagnostic_dir(self.data_dir)
        default_name = f"KR_Android_Diagnostic_{ts}.zip"
        if self.on_device:
            dest = default_dir / default_name
        else:
            chosen = filedialog.asksaveasfilename(
                title="Export Diagnostic ZIP",
                initialdir=str(default_dir),
                initialfile=default_name,
                defaultextension=".zip",
                filetypes=[("Diagnostic Archive (*.zip)", "*.zip")],
            )
            if not chosen:
                return
            dest = Path(chosen)

        res = adiag.export_diagnostic_bundle(self.data_dir, dest, self.hw_info, VERSION, self._game_dir())
        self._append_log(f"[DIAG] {res['message']}")
        if res["success"]:
            messagebox.showinfo("Diagnostic ZIP", f"{res['message']}\n\nSaved to:\n{res['path']}")
        else:
            messagebox.showerror("Diagnostic ZIP", res["message"])

    def _check_updates_async(self, silent: bool = False) -> None:
        if self.update_busy:
            return
        self.update_busy = True

        def worker() -> None:
            res = aupd.check_for_updates(VERSION, include_prereleases=True)

            def _done() -> None:
                self.update_busy = False
                self.update_info = res
                self._append_log(f"[UPDATE] {res['message']}")
                if not silent:
                    messagebox.showinfo("Update Check", res["message"])
                if not res.get("up_to_date", True) or self.active_tab == "settings":
                    self._build_ui()

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_update(self) -> None:
        if self.update_busy or not self.update_info or not self.update_info.get("download_url"):
            return
        self.update_busy = True
        url = self.update_info["download_url"]
        name = self.update_info.get("asset_name") or "KamenRiderMoH.nixport.zip"
        dest_dir = aupd.default_download_dir(self.data_dir)
        self._append_log(f"[UPDATE] Downloading {name} to {dest_dir}...")

        def worker() -> None:
            def prog(_pct: int, text: str) -> None:
                self.root.after(0, lambda m=text: self._append_log(f"[UPDATE] {m}"))

            res = aupd.download_port_zip(url, name, dest_dir, progress_cb=prog)

            def _done() -> None:
                self.update_busy = False
                self._append_log(f"[UPDATE] {res['message']}")
                if res["success"]:
                    messagebox.showinfo("Update Downloaded", res["message"])
                else:
                    messagebox.showerror("Update Failed", res["message"])

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_backup_saves(self) -> None:
        res = save_manager.backup_saves(self.data_dir)
        self._append_log(f"[SAVE] {res['message']}")
        if self.active_tab == "saves":
            self._render_active_tab()

    def _on_import_save_zip(self) -> None:
        initial = "/storage/emulated/0/Download" if os.path.isdir("/storage/emulated/0/Download") else str(self.data_dir)
        chosen = filedialog.askopenfilename(
            title="Import Save Archive (.zip)",
            initialdir=initial,
            filetypes=[("Save Archive (*.zip)", "*.zip")],
        )
        if not chosen:
            return
        res = save_manager.import_save_zip(self.data_dir, Path(chosen))
        self._append_log(f"[SAVE] {res['message']}")
        if res["success"]:
            messagebox.showinfo("Import Save", res["message"])
        else:
            messagebox.showerror("Import Save", res["message"])
        self._render_active_tab()

    def _on_select_backup(self, listbox: tk.Listbox) -> None:
        sel = listbox.curselection()
        if sel and hasattr(self, "_backup_names"):
            self.selected_backup = self._backup_names[sel[0]]

    def _on_restore_selected(self) -> None:
        if not self.selected_backup:
            return
        if not messagebox.askyesno(
            "Restore Save Backup",
            f"Restore save data from:\n{self.selected_backup}\n\n(A safety backup of your current saves will be created first.)",
        ):
            return
        res = save_manager.restore_backup(self.data_dir, self.selected_backup)
        self._append_log(f"[SAVE] {res['message']}")
        self._render_active_tab()

    def _trigger_indo_patch(self, enable: bool) -> None:
        if self.patch_busy or self.game_running:
            return
        gd = self._game_dir()
        if gd is None:
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return

        self.patch_busy = True
        self._patch_progress_text = self._tr("patch_busy")
        self._build_ui()

        def worker() -> None:
            def cb(msg: str) -> None:
                def _ui_update(m=msg):
                    self._patch_progress_text = m
                    self._append_log(m)
                    if hasattr(self, "patch_progress_lbl") and self.patch_progress_lbl.winfo_exists():
                        self.patch_progress_lbl.configure(text=m)
                self.root.after(0, _ui_update)

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
        self._patch_progress_text = res.get("message", "")
        self._append_log(f"[PATCH-ID] {self._patch_progress_text}")
        self._build_ui()

    def _on_play(self) -> None:
        if self.game_running or self.patch_busy:
            return
        gd = self._game_dir()
        if gd is None:
            messagebox.showwarning(self._tr("err_no_eboot_title"), self._tr("err_no_eboot_msg"))
            return

        acfg.sync_android_engine_config(self.data_dir, self.cfg)
        if self.cfg.get("auto_backup_saves", "true") == "true":
            ab = save_manager.auto_backup_saves(self.data_dir, keep=5)
            if ab.get("success"):
                self._append_log(f"[SAVE] {ab['message']}")

        runtime_bin = acfg.find_runtime_binary(self.app_dir, self.data_dir)
        if runtime_bin is None:
            self._append_log("[LAUNCH] ARM64 runtime binary (bin/kr_core) not bundled yet; config synced.")
            messagebox.showinfo(
                self._tr("err_no_runtime_title"),
                self._tr("err_no_runtime_msg", data_dir=str(self.data_dir)),
            )
            return

        eboot = gd / "eboot.bin"
        game_args = [str(runtime_bin), "-g", str(eboot.resolve()), "-f", "true"]
        if self.cfg.get("show_fps") == "true":
            game_args.append("--show-fps")

        env = dict(os.environ)
        env["HOME"] = str(self.data_dir.parent)
        env["XDG_DATA_HOME"] = str(self.data_dir / "bin" / "user")
        if self.cfg.get("video_backend", "auto") != "auto":
            env["SDL_VIDEODRIVER"] = self.cfg["video_backend"]

        fxd_root = Path(os.environ.get("FXD_ROOT", "/data/user/0/ro.cobrabm.fexdroid/files/rootfs"))
        loader = fxd_root / "usr" / "lib" / "aarch64-linux-gnu" / "ld-linux-aarch64.so.1"
        lib_parts = []
        if (self.app_dir / "lib").is_dir():
            lib_parts.append(str(self.app_dir / "lib"))
        if (fxd_root / "usr" / "lib" / "aarch64-linux-gnu").is_dir():
            lib_parts.append(str(fxd_root / "usr" / "lib" / "aarch64-linux-gnu"))
        if (fxd_root / "usr" / "lib").is_dir():
            lib_parts.append(str(fxd_root / "usr" / "lib"))
        if env.get("LD_LIBRARY_PATH"):
            lib_parts.append(env["LD_LIBRARY_PATH"])
        if lib_parts:
            env["LD_LIBRARY_PATH"] = ":".join(lib_parts)

        # Restore nixport virtual gamepad preload ONLY for the game binary (not Python)
        pad_preload = env.get("KR_SAVED_LD_PRELOAD", "").strip()
        if not pad_preload:
            pad_so = fxd_root / "usr" / "lib" / "fexdroid" / "libfexpad.so"
            if pad_so.is_file():
                pad_preload = str(pad_so)
        if pad_preload:
            env["LD_PRELOAD"] = pad_preload

        if sys.platform != "win32" and not Path("/lib/ld-linux-aarch64.so.1").exists() and loader.is_file():
            cmd = [str(loader), "--library-path", env.get("LD_LIBRARY_PATH", ""), *game_args]
        else:
            cmd = game_args

        run_cwd = self.data_dir / "bin"
        run_cwd.mkdir(parents=True, exist_ok=True)

        log_path = acfg.get_log_dir(self.data_dir) / "launch.log"
        self._append_log(f"[LAUNCH] Executing: {' '.join(cmd)}")
        self.game_running = True
        self._build_ui()

        t_start = time.monotonic()

        def run_proc() -> None:
            rc = -1
            try:
                with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
                    lf.write(f"=== Kamen Rider: Memory of Heroes Launch ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    lf.write(f"CWD: {run_cwd}\n")
                    lf.write(f"CMD: {' '.join(cmd)}\n\n")
                    lf.flush()
                    proc = subprocess.Popen(cmd, cwd=str(run_cwd), env=env, stdout=lf, stderr=subprocess.STDOUT)
                    rc = proc.wait()
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._append_log(f"[LAUNCH ERROR] {e}"))
            finally:
                dur = time.monotonic() - t_start
                session_tracker.record_session(self.data_dir, dur, rc)
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
    app = KRAndroidLauncher(root, skip_network=args.smoke_test)
    if args.smoke_test:
        for tab in ("play", "patch", "saves", "trophies", "settings"):
            app._switch_tab(tab)
            root.update_idletasks()
        app._toggle_theme()
        app._cycle_language()
        root.update_idletasks()
        root.destroy()
        print("[SMOKE-TEST] Clean UI v1.0.0 launcher initialized & rendered all 5 tabs + Dark/Light + 5-Lang OK.")
        return 0

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
