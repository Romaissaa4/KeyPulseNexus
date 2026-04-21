from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk

import customtkinter as ctk
import matplotlib.pyplot as plt


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR

LOG_FILE = APP_DIR / "keypulse_nexus_log.txt"
SUMMARY_FILE = APP_DIR / "keypulse_nexus_brief.txt"
ICON_FILE = RESOURCE_DIR / "icon.ico"

SURFACE = "#07121f"
PANEL = "#0d1c30"
PANEL_ALT = "#10243d"
STREAM_BG = "#08111d"
BORDER = "#214e78"
TEXT = "#edf5ff"
MUTED = "#9db3d1"
ACCENT = "#16c6e5"
ACCENT_ALT = "#ffb347"
SUCCESS = "#33d69f"
DANGER = "#ff6b7a"
WARNING = "#f5b74f"

PRINTABLE_SPECIALS = {
    " ": "SPACE",
    "\n": "ENTER",
    "\t": "TAB",
}

KEY_LABELS = {
    "BackSpace": "BACKSPACE",
    "Return": "ENTER",
    "space": "SPACE",
    "Tab": "TAB",
    "Escape": "ESC",
    "Delete": "DELETE",
    "Insert": "INSERT",
    "Home": "HOME",
    "End": "END",
    "Prior": "PAGE UP",
    "Next": "PAGE DOWN",
    "Left": "LEFT",
    "Right": "RIGHT",
    "Up": "UP",
    "Down": "DOWN",
    "Shift_L": "SHIFT",
    "Shift_R": "SHIFT",
    "Control_L": "CTRL",
    "Control_R": "CTRL",
    "Alt_L": "ALT",
    "Alt_R": "ALT",
    "Caps_Lock": "CAPS LOCK",
}


def blend(color_a: str, color_b: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    first = tuple(int(color_a[index : index + 2], 16) for index in (1, 3, 5))
    second = tuple(int(color_b[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(int(a + (b - a) * ratio) for a, b in zip(first, second))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def write_log(line: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line)


class KeyPulseNexusApp:
    def __init__(self) -> None:
        self.app = ctk.CTk()
        self.app.title("KeyPulse Nexus")
        self.app.geometry("1240x820")
        self.app.minsize(1120, 760)
        self.app.configure(fg_color=SURFACE)
        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(0, weight=1)

        try:
            if ICON_FILE.exists():
                self.app.iconbitmap(str(ICON_FILE))
        except Exception:
            pass

        self.session_active = False
        self.session_index = 0
        self.session_started_at: float | None = None
        self.total_keys = 0
        self.printable_keys = 0
        self.key_frequency: Counter[str] = Counter()
        self.stream_events: deque[str] = deque(maxlen=14)
        self.last_key = "--"
        self.placeholder_visible = True

        self.background_canvas = tk.Canvas(
            self.app,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.background_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.background_canvas.bind("<Configure>", self.draw_background)

        self.shell = ctk.CTkFrame(self.app, fg_color="transparent")
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.shell.grid_columnconfigure(0, weight=0, minsize=290)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_columnconfigure(2, weight=0, minsize=320)
        self.shell.grid_rowconfigure(1, weight=1)

        self.build_header()
        self.build_left_panel()
        self.build_center_panel()
        self.build_right_panel()

        self.refresh_dashboard()
        self.refresh_stream()
        self.animate_badge()
        self.tick_clock()
        self.draw_background()

    def build_header(self) -> None:
        header = ctk.CTkFrame(
            self.shell,
            fg_color=PANEL,
            corner_radius=28,
            border_width=1,
            border_color=BORDER,
        )
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=24, pady=(22, 14))
        header.grid_columnconfigure(0, weight=1)

        text_column = ctk.CTkFrame(header, fg_color="transparent")
        text_column.grid(row=0, column=0, sticky="w", padx=26, pady=24)

        ctk.CTkLabel(
            text_column,
            text="KeyPulse Nexus",
            font=("Bahnschrift SemiBold", 34),
            text_color=TEXT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_column,
            text="Classroom-safe keyboard analytics sandbox with live metrics, session logs, and polished demo visuals.",
            font=("Segoe UI", 14),
            text_color=MUTED,
            wraplength=660,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

        badge_column = ctk.CTkFrame(header, fg_color="transparent")
        badge_column.grid(row=0, column=1, sticky="e", padx=26, pady=22)

        self.status_badge = ctk.CTkLabel(
            badge_column,
            text="Idle Session",
            width=180,
            height=38,
            corner_radius=18,
            fg_color="#20344d",
            text_color=TEXT,
            font=("Bahnschrift SemiBold", 15),
        )
        self.status_badge.pack(anchor="e")

        self.scope_badge = ctk.CTkLabel(
            badge_column,
            text="App-local only",
            width=180,
            height=34,
            corner_radius=17,
            fg_color="#16314a",
            text_color="#a9dfff",
            font=("Bahnschrift SemiBold", 14),
        )
        self.scope_badge.pack(anchor="e", pady=(10, 8))

        self.timer_label = ctk.CTkLabel(
            badge_column,
            text="00:00",
            font=("Cascadia Code", 28),
            text_color=ACCENT,
        )
        self.timer_label.pack(anchor="e")

    def build_left_panel(self) -> None:
        panel = ctk.CTkFrame(
            self.shell,
            fg_color=PANEL,
            corner_radius=28,
            border_width=1,
            border_color=BORDER,
        )
        panel.grid(row=1, column=0, sticky="nsew", padx=(24, 14), pady=(0, 24))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Mission Control",
            font=("Bahnschrift SemiBold", 24),
            text_color=TEXT,
        ).pack(anchor="w", padx=22, pady=(22, 6))

        ctk.CTkLabel(
            panel,
            text="Start a monitored typing session, generate a clean activity log, and present the analytics in a professor-friendly way.",
            font=("Segoe UI", 13),
            text_color=MUTED,
            wraplength=240,
            justify="left",
        ).pack(anchor="w", padx=22)

        self.start_button = ctk.CTkButton(
            panel,
            text="Start Session",
            height=48,
            corner_radius=16,
            fg_color=SUCCESS,
            hover_color="#22b988",
            text_color="#04111a",
            font=("Bahnschrift SemiBold", 17),
            command=self.start_session,
        )
        self.start_button.pack(fill="x", padx=22, pady=(22, 10))

        self.stop_button = ctk.CTkButton(
            panel,
            text="Stop Session",
            height=46,
            corner_radius=16,
            fg_color=DANGER,
            hover_color="#e05464",
            font=("Bahnschrift SemiBold", 16),
            command=self.stop_session,
        )
        self.stop_button.pack(fill="x", padx=22, pady=6)

        self.open_button = ctk.CTkButton(
            panel,
            text="Open Log File",
            height=44,
            corner_radius=16,
            fg_color=PANEL_ALT,
            hover_color="#193252",
            font=("Bahnschrift SemiBold", 15),
            command=self.open_log,
        )
        self.open_button.pack(fill="x", padx=22, pady=6)

        self.report_button = ctk.CTkButton(
            panel,
            text="Show Frequency Report",
            height=44,
            corner_radius=16,
            fg_color=ACCENT_ALT,
            hover_color="#dc9736",
            text_color="#101620",
            font=("Bahnschrift SemiBold", 15),
            command=self.show_report,
        )
        self.report_button.pack(fill="x", padx=22, pady=6)

        self.summary_button = ctk.CTkButton(
            panel,
            text="Export Session Brief",
            height=44,
            corner_radius=16,
            fg_color="#2a4f76",
            hover_color="#244566",
            font=("Bahnschrift SemiBold", 15),
            command=self.export_summary,
        )
        self.summary_button.pack(fill="x", padx=22, pady=6)

        self.clear_button = ctk.CTkButton(
            panel,
            text="Clear Session Data",
            height=42,
            corner_radius=16,
            fg_color="#243952",
            hover_color="#1b2c40",
            font=("Bahnschrift SemiBold", 15),
            command=self.clear_session,
        )
        self.clear_button.pack(fill="x", padx=22, pady=(6, 18))

        divider = ctk.CTkFrame(panel, fg_color="#17314d", height=1)
        divider.pack(fill="x", padx=22, pady=8)

        ctk.CTkLabel(
            panel,
            text="Live Intensity",
            font=("Bahnschrift SemiBold", 16),
            text_color=TEXT,
        ).pack(anchor="w", padx=22, pady=(4, 6))

        self.intensity_label = ctk.CTkLabel(
            panel,
            text="0.00 keys/sec",
            font=("Cascadia Code", 14),
            text_color=MUTED,
        )
        self.intensity_label.pack(anchor="w", padx=22)

        self.intensity_bar = ctk.CTkProgressBar(
            panel,
            height=14,
            corner_radius=12,
            progress_color=ACCENT,
            fg_color="#12263e",
        )
        self.intensity_bar.pack(fill="x", padx=22, pady=(10, 18))
        self.intensity_bar.set(0)

        notes = ctk.CTkFrame(
            panel,
            fg_color=PANEL_ALT,
            corner_radius=22,
            border_width=1,
            border_color="#183a5a",
        )
        notes.pack(fill="x", padx=22, pady=(0, 18))

        ctk.CTkLabel(
            notes,
            text="Lab Notes",
            font=("Bahnschrift SemiBold", 16),
            text_color=TEXT,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self.notice_label = ctk.CTkLabel(
            notes,
            text="App-local monitoring only. Nothing is captured outside the typing pad.",
            font=("Segoe UI", 12),
            text_color=MUTED,
            justify="left",
            wraplength=220,
        )
        self.notice_label.pack(anchor="w", padx=16, pady=(0, 12))

        self.log_file_label = ctk.CTkLabel(
            notes,
            text=f"Log: {LOG_FILE.name}",
            font=("Cascadia Code", 11),
            text_color="#c7d8ef",
            justify="left",
        )
        self.log_file_label.pack(anchor="w", padx=16, pady=(0, 14))

    def build_center_panel(self) -> None:
        panel = ctk.CTkFrame(
            self.shell,
            fg_color=PANEL,
            corner_radius=28,
            border_width=1,
            border_color=BORDER,
        )
        panel.grid(row=1, column=1, sticky="nsew", padx=0, pady=(0, 24))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            panel,
            text="Typing Deck",
            font=("Bahnschrift SemiBold", 24),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 6))

        ctk.CTkLabel(
            panel,
            text="Press Start Session, then type inside this sandbox to feed the dashboard. Great for a live classroom demonstration.",
            font=("Segoe UI", 13),
            text_color=MUTED,
            justify="left",
            wraplength=620,
        ).grid(row=0, column=0, sticky="e", padx=22, pady=(28, 0))

        self.typing_box = ctk.CTkTextbox(
            panel,
            corner_radius=24,
            fg_color=STREAM_BG,
            text_color=TEXT,
            border_width=1,
            border_color="#183553",
            font=("Cascadia Code", 15),
            wrap="word",
        )
        self.typing_box.grid(row=1, column=0, sticky="nsew", padx=22, pady=(14, 18))
        self.typing_box.insert(
            "1.0",
            "Press Start Session to unlock the typing pad.\n\n"
            "Suggested live demo line:\n"
            "Ethical hacking projects should prioritize transparency, consent, and measurable analysis.",
        )
        self.typing_box.configure(state="disabled")
        self.typing_box.bind("<KeyPress>", self.handle_keypress)

        stream_frame = ctk.CTkFrame(
            panel,
            fg_color=PANEL_ALT,
            corner_radius=24,
            border_width=1,
            border_color="#183a5a",
        )
        stream_frame.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 22))
        stream_frame.grid_columnconfigure(0, weight=1)
        stream_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            stream_frame,
            text="Live Signal Feed",
            font=("Bahnschrift SemiBold", 18),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        self.stream_box = ctk.CTkTextbox(
            stream_frame,
            corner_radius=18,
            fg_color=STREAM_BG,
            text_color="#cfe1fb",
            border_width=0,
            font=("Cascadia Code", 12),
            activate_scrollbars=True,
            wrap="word",
        )
        self.stream_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.stream_box.configure(state="disabled")

    def build_right_panel(self) -> None:
        panel = ctk.CTkFrame(
            self.shell,
            fg_color=PANEL,
            corner_radius=28,
            border_width=1,
            border_color=BORDER,
        )
        panel.grid(row=1, column=2, sticky="nsew", padx=(14, 24), pady=(0, 24))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Analytics",
            font=("Bahnschrift SemiBold", 24),
            text_color=TEXT,
        ).pack(anchor="w", padx=22, pady=(22, 14))

        stats_grid = ctk.CTkFrame(panel, fg_color="transparent")
        stats_grid.pack(fill="x", padx=22)
        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)

        self.total_value, _ = self.make_stat_card(stats_grid, 0, 0, "Total Keys", "Session volume")
        self.unique_value, _ = self.make_stat_card(stats_grid, 0, 1, "Unique Keys", "Pattern spread")
        self.top_key_value, _ = self.make_stat_card(stats_grid, 1, 0, "Top Key", "Most frequent")
        self.rhythm_value, self.rhythm_hint = self.make_stat_card(stats_grid, 1, 1, "Rhythm", "Current pace")

        chart_frame = ctk.CTkFrame(
            panel,
            fg_color=PANEL_ALT,
            corner_radius=24,
            border_width=1,
            border_color="#183a5a",
        )
        chart_frame.pack(fill="both", expand=True, padx=22, pady=(18, 14))
        chart_frame.pack_propagate(False)

        ctk.CTkLabel(
            chart_frame,
            text="Top Frequency Pulse",
            font=("Bahnschrift SemiBold", 18),
            text_color=TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            chart_frame,
            text="Live top-five key distribution for the active session.",
            font=("Segoe UI", 12),
            text_color=MUTED,
        ).pack(anchor="w", padx=18)

        self.chart_canvas = tk.Canvas(
            chart_frame,
            height=230,
            highlightthickness=0,
            bd=0,
            bg=STREAM_BG,
        )
        self.chart_canvas.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        self.chart_canvas.bind("<Configure>", lambda _: self.draw_frequency_chart())

        summary = ctk.CTkFrame(
            panel,
            fg_color=PANEL_ALT,
            corner_radius=22,
            border_width=1,
            border_color="#183a5a",
        )
        summary.pack(fill="x", padx=22, pady=(0, 22))

        ctk.CTkLabel(
            summary,
            text="Session Snapshot",
            font=("Bahnschrift SemiBold", 16),
            text_color=TEXT,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self.snapshot_label = ctk.CTkLabel(
            summary,
            text="Last event: --\nMode: Waiting for session start",
            font=("Segoe UI", 12),
            text_color=MUTED,
            justify="left",
        )
        self.snapshot_label.pack(anchor="w", padx=16, pady=(0, 14))

    def make_stat_card(
        self,
        parent: ctk.CTkFrame,
        row: int,
        column: int,
        title: str,
        subtitle: str,
    ) -> tuple[ctk.CTkLabel, ctk.CTkLabel]:
        card = ctk.CTkFrame(
            parent,
            fg_color=PANEL_ALT,
            corner_radius=22,
            border_width=1,
            border_color="#183a5a",
        )
        card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Bahnschrift SemiBold", 15),
            text_color=MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        value = ctk.CTkLabel(
            card,
            text="0",
            font=("Bahnschrift SemiBold", 28),
            text_color=TEXT,
        )
        value.pack(anchor="w", padx=16)

        hint = ctk.CTkLabel(
            card,
            text=subtitle,
            font=("Cascadia Code", 11),
            text_color="#c2d3ea",
        )
        hint.pack(anchor="w", padx=16, pady=(2, 14))
        return value, hint

    def draw_background(self, _event: tk.Event | None = None) -> None:
        width = max(1, self.app.winfo_width())
        height = max(1, self.app.winfo_height())
        self.background_canvas.delete("all")

        steps = max(220, height // 2)
        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            color = blend("#04101a", "#12385e", ratio)
            y0 = int(index * height / steps)
            y1 = int((index + 1) * height / steps) + 1
            self.background_canvas.create_rectangle(0, y0, width, y1, outline="", fill=color)

        self.background_canvas.create_oval(
            width * 0.58,
            -height * 0.10,
            width * 1.08,
            height * 0.58,
            fill="#0b2440",
            outline="",
        )
        self.background_canvas.create_oval(
            -width * 0.16,
            height * 0.56,
            width * 0.32,
            height * 1.10,
            fill="#081b30",
            outline="",
        )
        self.background_canvas.create_rectangle(
            0,
            height * 0.34,
            width,
            height * 0.345,
            fill="#1a5f8d",
            outline="",
        )
    def normalize_key(self, event: tk.Event) -> tuple[str, str, bool]:
        if event.char in PRINTABLE_SPECIALS:
            label = PRINTABLE_SPECIALS[event.char]
            token = event.char
            return label, token, True

        if event.char and event.char.isprintable():
            label = event.char.upper()
            return label, event.char, True

        label = KEY_LABELS.get(event.keysym, event.keysym.upper())
        return label, f"<{label}>", False

    def set_notice(self, message: str, color: str = MUTED) -> None:
        self.notice_label.configure(text=message, text_color=color)

    def start_session(self) -> None:
        if self.session_active:
            self.set_notice("A session is already running. Type inside the pad to feed the dashboard.", ACCENT)
            self.typing_box.focus_set()
            return

        self.session_active = True
        self.session_index += 1
        self.session_started_at = time.time()
        self.status_badge.configure(text="Live Session")
        self.set_notice("Session armed. The typing pad is now collecting local keystrokes.", SUCCESS)

        if self.placeholder_visible:
            self.typing_box.configure(state="normal")
            self.typing_box.delete("1.0", "end")
            self.placeholder_visible = False
        else:
            self.typing_box.configure(state="normal")

        self.typing_box.focus_set()

        write_log(
            f"\n=== Session {self.session_index} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
        )
        self.stream_events.appendleft(f"[{datetime.now().strftime('%H:%M:%S')}] Session {self.session_index} started")
        self.refresh_stream()
        self.refresh_dashboard()

    def stop_session(self) -> None:
        if not self.session_active:
            self.set_notice("No active session. Start one to unlock the typing pad.", WARNING)
            return

        self.session_active = False
        self.status_badge.configure(text="Idle Session")
        self.typing_box.configure(state="disabled")
        self.set_notice("Session stopped. Metrics stay visible for presentation and review.", MUTED)
        write_log(f"--- Session {self.session_index} stopped at {datetime.now().strftime('%H:%M:%S')} ---\n")
        self.stream_events.appendleft(f"[{datetime.now().strftime('%H:%M:%S')}] Session stopped")
        self.refresh_stream()
        self.refresh_dashboard()

    def clear_session(self) -> None:
        self.session_active = False
        self.session_started_at = None
        self.total_keys = 0
        self.printable_keys = 0
        self.key_frequency.clear()
        self.stream_events.clear()
        self.last_key = "--"
        self.status_badge.configure(text="Idle Session")
        self.set_notice("All session data cleared. Start a fresh demo when ready.", MUTED)

        self.typing_box.configure(state="normal")
        self.typing_box.delete("1.0", "end")
        self.typing_box.insert(
            "1.0",
            "Press Start Session to unlock the typing pad.\n\n"
            "Suggested live demo line:\n"
            "Ethical hacking projects should prioritize transparency, consent, and measurable analysis.",
        )
        self.typing_box.configure(state="disabled")
        self.placeholder_visible = True

        LOG_FILE.write_text("", encoding="utf-8")
        self.refresh_stream()
        self.refresh_dashboard()

    def open_log(self) -> None:
        if not LOG_FILE.exists():
            LOG_FILE.write_text("", encoding="utf-8")

        try:
            subprocess.Popen(["notepad", str(LOG_FILE)])
            self.set_notice("Log file opened in Notepad.", ACCENT)
        except Exception:
            self.set_notice("Could not open Notepad on this machine.", DANGER)

    def export_summary(self) -> None:
        if not self.key_frequency:
            self.set_notice("No session data yet. Run a session before exporting the brief.", WARNING)
            return

        elapsed = time.time() - self.session_started_at if self.session_started_at is not None else 0.0
        top_items = self.key_frequency.most_common(5)
        printable_ratio = (self.printable_keys / self.total_keys * 100) if self.total_keys else 0.0

        lines = [
            "KeyPulse Nexus - Session Brief",
            "=" * 42,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session ID: {self.session_index}",
            f"Current Mode: {'Live' if self.session_active else 'Stopped'}",
            f"Elapsed Time: {format_elapsed(elapsed)}",
            f"Total Keys: {self.total_keys}",
            f"Unique Keys: {len(self.key_frequency)}",
            f"Printable Ratio: {printable_ratio:.1f}%",
            f"Last Event: {self.last_key}",
            "",
            "Top Keys:",
        ]

        for label, count in top_items:
            lines.append(f"- {label}: {count}")

        lines.extend(
            [
                "",
                "Note:",
                "This classroom demo only analyzes typing inside the application sandbox.",
            ]
        )

        SUMMARY_FILE.write_text("\n".join(lines), encoding="utf-8")

        try:
            subprocess.Popen(["notepad", str(SUMMARY_FILE)])
            self.set_notice("Session brief exported and opened in Notepad.", ACCENT)
        except Exception:
            self.set_notice("Session brief exported successfully.", ACCENT)

    def handle_keypress(self, event: tk.Event) -> str | None:
        if not self.session_active:
            return "break"

        label, token, printable = self.normalize_key(event)
        self.total_keys += 1
        self.last_key = label
        self.key_frequency[label] += 1

        if printable:
            self.printable_keys += 1

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.stream_events.appendleft(f"[{timestamp}] {label}")
        self.refresh_stream()
        write_log(f"[{timestamp}] {token}\n")
        self.refresh_dashboard()
        return None

    def refresh_stream(self) -> None:
        content = "\n".join(self.stream_events) if self.stream_events else "Waiting for your first session event."
        self.stream_box.configure(state="normal")
        self.stream_box.delete("1.0", "end")
        self.stream_box.insert("1.0", content)
        self.stream_box.configure(state="disabled")

    def refresh_dashboard(self) -> None:
        elapsed = 0.0
        if self.session_started_at is not None:
            elapsed = time.time() - self.session_started_at

        pace = self.total_keys / elapsed if elapsed > 0 else 0.0
        unique_keys = len(self.key_frequency)
        top_key = self.key_frequency.most_common(1)[0][0] if self.key_frequency else "--"
        ratio = (self.printable_keys / self.total_keys * 100) if self.total_keys else 0.0

        self.total_value.configure(text=str(self.total_keys))
        self.unique_value.configure(text=str(unique_keys))
        self.top_key_value.configure(text=top_key)
        self.rhythm_value.configure(text=f"{pace:.2f}")
        self.rhythm_hint.configure(text=f"{ratio:.0f}% printable")

        self.timer_label.configure(text=format_elapsed(elapsed))
        self.intensity_label.configure(text=f"{pace:.2f} keys/sec")
        self.intensity_bar.set(min(pace / 8, 1))
        mode_text = "Recording inside typing pad" if self.session_active else "Waiting for session start"
        self.snapshot_label.configure(text=f"Last event: {self.last_key}\nMode: {mode_text}")
        self.draw_frequency_chart()

    def draw_frequency_chart(self) -> None:
        self.chart_canvas.delete("all")

        width = max(320, self.chart_canvas.winfo_width())
        height = max(230, self.chart_canvas.winfo_height())
        self.chart_canvas.create_rectangle(0, 0, width, height, fill=STREAM_BG, outline="")

        top_items = self.key_frequency.most_common(5)
        if not top_items:
            self.chart_canvas.create_text(
                width / 2,
                height / 2,
                text="No session data yet",
                fill="#9cb0cb",
                font=("Bahnschrift SemiBold", 18),
            )
            self.chart_canvas.create_text(
                width / 2,
                height / 2 + 28,
                text="Start a session and type inside the lab pad.",
                fill="#7089a8",
                font=("Segoe UI", 11),
            )
            return

        colors = [ACCENT, "#4ad8b5", ACCENT_ALT, "#7aa8ff", "#ff7c8d"]
        bar_area_height = height - 72
        max_value = top_items[0][1]
        spacing = width / max(len(top_items), 1)
        bar_width = min(44, spacing * 0.5)

        for index, (label, value) in enumerate(top_items):
            center_x = spacing * index + spacing / 2
            x0 = center_x - bar_width / 2
            x1 = center_x + bar_width / 2
            y1 = height - 34
            y0 = y1 - (value / max_value) * bar_area_height
            color = colors[index % len(colors)]

            self.chart_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            self.chart_canvas.create_text(
                center_x,
                y0 - 12,
                text=str(value),
                fill="#d8e6fb",
                font=("Cascadia Code", 10),
            )
            self.chart_canvas.create_text(
                center_x,
                height - 16,
                text=label[:8],
                fill="#b6c8e3",
                font=("Bahnschrift SemiBold", 10),
            )

    def animate_badge(self) -> None:
        if self.session_active:
            pulse = time.time() % 1
            color = blend("#0d8aa2", "#1fd3a2", pulse)
            text_color = "#03121c"
        else:
            color = "#20344d"
            text_color = TEXT

        self.status_badge.configure(fg_color=color, text_color=text_color)
        self.app.after(220, self.animate_badge)

    def tick_clock(self) -> None:
        self.refresh_dashboard()
        self.app.after(250, self.tick_clock)

    def show_report(self) -> None:
        if not self.key_frequency:
            self.set_notice("No key data yet. Start a session and type before opening the report.", WARNING)
            return

        top_items = self.key_frequency.most_common(10)
        labels = [item[0] for item in top_items]
        values = [item[1] for item in top_items]
        colors = [ACCENT, "#4ad8b5", ACCENT_ALT, "#7aa8ff", "#ff7c8d"] * 2

        plt.style.use("dark_background")
        figure, axis = plt.subplots(figsize=(11, 5.5), facecolor="#07121f")
        axis.set_facecolor("#0d1c30")

        bars = axis.bar(labels, values, color=colors[: len(values)], width=0.62)
        axis.set_title("KeyPulse Nexus Frequency Report", fontsize=18, color=TEXT, pad=14)
        axis.set_xlabel("Key", color="#b9cee7")
        axis.set_ylabel("Count", color="#b9cee7")
        axis.tick_params(colors="#d9e8ff")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#4f6d8d")
        axis.spines["bottom"].set_color("#4f6d8d")
        axis.grid(axis="y", color="#1e3855", linestyle="--", linewidth=0.7, alpha=0.8)

        for bar, value in zip(bars, values):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.15,
                str(value),
                ha="center",
                va="bottom",
                fontsize=10,
                color="#d9e8ff",
            )

        figure.tight_layout()
        self.set_notice("Frequency report opened in a Matplotlib window.", ACCENT)
        plt.show()

    def run(self) -> None:
        self.app.mainloop()


if __name__ == "__main__":
    KeyPulseNexusApp().run()
