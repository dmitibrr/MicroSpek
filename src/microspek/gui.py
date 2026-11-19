"""Tkinter GUI for MicroSpek."""

from __future__ import annotations

import queue
import threading
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .collectors import sensors as sensor_hub
from .i18n import get_language, localize_snapshot, s, set_language, t
from .models import format_bytes
from .render import SEGMENT_COLORS, default_name, save_snapshot
from .snapshot import collect_snapshot

BG = "#eef1f5"
PANEL = "#e6ebf2"
CARD = "#ffffff"
INK = "#232c38"
MUTED = "#7b8798"
ACCENT = "#2f7dd1"
ACCENT_ACTIVE = "#2568b4"
BORDER = "#d3dae4"
ROW_ODD = "#f7f9fc"
GROUP_BG = "#e9eff8"
SENSITIVE = "#9b5318"
OK = "#3fae8e"
WARN = "#d08b2c"
ERROR = "#c0503f"


class MicroSpekApp(tk.Tk):
    """Main window with a summary tab, per-section tabs and disk layout canvas."""

    def __init__(self, snapshot=None) -> None:
        super().__init__()
        self._language = get_language()
        self.title(s("app_title"))
        self.geometry("1180x780")
        self.minsize(920, 580)
        self.configure(background=BG)

        self.snapshot = snapshot
        self._view = None
        self._layouts = []
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        self._tab_frames: list[ttk.Frame] = []
        self._status_text = s("status_ready")
        self._status_kind = "idle"
        self._redact = tk.BooleanVar(value=False)
        self._dxdiag = tk.BooleanVar(value=False)
        self._lang = tk.StringVar(value="RU" if self._language == "ru" else "EN")
        self._status_var = tk.StringVar(value=self._status_text)
        self.elevate_sensors = False

        self._style()
        self._grid()
        self._build_header()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        self.bind("<Control-r>", lambda _event: self.refresh())
        if snapshot is not None:
            self._layouts = list(snapshot.layouts)
            self._rebuild_tabs()
            self._set_status(
                s("status_loaded", time=snapshot.generated_at.strftime("%H:%M:%S")), "ok"
            )
        else:
            self.refresh()
        self.after(120, self._poll)

    # ------------------------------------------------------------------- styling

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 9), background=BG, foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Bar.TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Card.TLabel", background=CARD, foreground=INK)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 17), foreground=INK)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9), foreground=MUTED)
        style.configure("Hint.TLabel", font=("Segoe UI", 8), foreground=MUTED)
        style.configure("Version.TLabel", font=("Segoe UI", 8), foreground=MUTED)
        style.configure(
            "TButton",
            padding=(13, 7),
            background=PANEL,
            foreground=INK,
            borderwidth=0,
            focusthickness=0,
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("pressed", "#d6dde8"), ("active", "#dde4ee")],
            foreground=[("disabled", "#a6b0bd")],
        )
        style.configure(
            "Accent.TButton",
            padding=(15, 7),
            background=ACCENT,
            foreground="#ffffff",
            font=("Segoe UI Semibold", 9),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", ACCENT_ACTIVE), ("active", ACCENT_ACTIVE)],
            foreground=[("disabled", "#e3eaf4")],
        )
        style.configure(
            "TMenubutton",
            padding=(13, 7),
            background=PANEL,
            foreground=INK,
            borderwidth=0,
            relief="flat",
            arrowcolor=INK,
        )
        style.map("TMenubutton", background=[("active", "#dde4ee"), ("pressed", "#d6dde8")])
        style.configure("TCheckbutton", background=BG, foreground=INK, padding=(2, 2))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TCombobox", padding=3, arrowsize=13, fieldbackground=CARD)
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab",
            padding=(15, 7),
            background="#e0e6ee",
            foreground=MUTED,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", CARD), ("active", "#e9eff7")],
            foreground=[("selected", INK)],
        )
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=INK,
            rowheight=26,
            borderwidth=0,
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#dce9f8")], foreground=[("selected", INK)])
        style.configure(
            "Treeview.Heading",
            background="#e9eef5",
            foreground=INK,
            font=("Segoe UI Semibold", 9),
            padding=(8, 6),
            relief="flat",
            borderwidth=0,
        )
        style.map("Treeview.Heading", background=[("active", "#e2e9f3")])
        style.configure(
            "Vertical.TScrollbar",
            background="#dbe2ec",
            troughcolor=BG,
            borderwidth=0,
            arrowsize=12,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background="#dbe2ec",
            troughcolor=BG,
            borderwidth=0,
            arrowsize=12,
        )
        style.configure("TSeparator", background=BORDER)

    def _grid(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

    # --------------------------------------------------------------- chrome build

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(20, 16, 20, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        self._header = header

        left = ttk.Frame(header)
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="MicroSpek", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text=s("app_subtitle"), style="Subtitle.TLabel").pack(anchor="w", pady=(1, 0))

        right = ttk.Frame(header)
        right.grid(row=0, column=1, sticky="e")
        ttk.Label(right, text=s("language"), style="Hint.TLabel").pack(side="left", padx=(0, 6))
        combo = ttk.Combobox(
            right,
            textvariable=self._lang,
            values=("RU", "EN"),
            width=4,
            state="readonly",
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self._on_language_change)
        ttk.Label(right, text=f"v{__version__}", style="Version.TLabel").pack(
            side="left", padx=(12, 0)
        )

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(14, 0, 14, 10))
        bar.grid(row=1, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        self._toolbar = bar

        left = ttk.Frame(bar)
        left.grid(row=0, column=0, sticky="w")
        ttk.Button(left, text=s("refresh"), style="Accent.TButton", command=self.refresh).pack(
            side="left"
        )
        ttk.Button(left, text=s("sensors_admin"), command=self.elevate_and_refresh).pack(
            side="left", padx=(8, 0)
        )
        ttk.Separator(left, orient="vertical").pack(side="left", fill="y", padx=12, pady=2)
        ttk.Button(left, text=s("screenshot"), command=self.screenshot).pack(side="left", padx=(8, 0))

        menu = tk.Menu(
            self,
            tearoff=0,
            background=CARD,
            foreground=INK,
            activebackground="#e2ecf9",
            activeforeground=INK,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        menu.add_command(label=s("export_txt"), command=lambda: self.export("txt"))
        menu.add_command(label=s("export_json"), command=lambda: self.export("json"))
        menu.add_command(label=s("export_md"), command=lambda: self.export("md"))
        menubutton = ttk.Menubutton(left, text=s("export"), style="TMenubutton", menu=menu)
        menubutton.pack(side="left", padx=(8, 0))
        self._export_menu = menu

        right = ttk.Frame(bar)
        right.grid(row=0, column=1, sticky="e")
        ttk.Checkbutton(right, text=s("redact"), variable=self._redact).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(right, text=s("dxdiag"), variable=self._dxdiag).pack(side="left", padx=(10, 0))

    def _build_notebook(self) -> None:
        wrap = ttk.Frame(self, padding=(14, 0, 14, 6))
        wrap.grid(row=2, column=0, sticky="nsew")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self._notebook_wrap = wrap
        self.notebook = ttk.Notebook(wrap)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.after(30, self._draw_layouts))

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, padding=(18, 0, 18, 10))
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        self._statusbar = bar
        self._status_dot = tk.Canvas(
            bar, width=10, height=10, highlightthickness=0, background=BG
        )
        self._status_dot.grid(row=0, column=0, sticky="w", padx=(0, 7))
        self._dot = self._status_dot.create_oval(1, 1, 9, 9, fill=OK, outline="")
        ttk.Label(bar, textvariable=self._status_var, style="Hint.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(bar, text=f"MicroSpek {__version__} · Unlicense", style="Version.TLabel").grid(
            row=0, column=2, sticky="e"
        )

    def _set_status(self, text: str, kind: str = "idle") -> None:
        self._status_text = text
        self._status_kind = kind
        self._status_var.set(text)
        colors = {"idle": OK, "busy": WARN, "error": ERROR, "ok": OK}
        try:
            self._status_dot.itemconfigure(self._dot, fill=colors.get(kind, OK))
        except (tk.TclError, AttributeError):
            pass

    def _on_language_change(self, _event=None) -> None:
        language = "ru" if self._lang.get().upper() == "RU" else "en"
        if language == self._language:
            return
        self._language = set_language(language)
        self.title(s("app_title"))
        for frame in (self._header, self._toolbar, self._statusbar):
            frame.destroy()
        self._build_header()
        self._build_toolbar()
        self._build_statusbar()
        self._rebuild_tabs()
        self._set_status(self._localized_status(), self._status_kind)

    def _localized_status(self) -> str:
        # Status strings are stored translated; re-create the common ones.
        if self._status_kind == "busy":
            return s("status_collecting")
        if self.snapshot is None:
            return s("status_ready")
        return s(
            "status_loaded",
            time=self.snapshot.generated_at.strftime("%H:%M:%S"),
        )

    # ------------------------------------------------------------------ collection

    def refresh(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status(s("status_collecting"), "busy")
        threading.Thread(
            target=self._worker,
            args=(self._dxdiag.get(), self.elevate_sensors),
            daemon=True,
        ).start()

    def elevate_and_refresh(self) -> None:
        """Collect sensors again, this time through a UAC prompt."""
        sensor_hub.reset()
        self.elevate_sensors = True
        self.refresh()

    def _worker(self, include_dxdiag: bool, elevate_sensors: bool) -> None:
        try:
            snapshot = collect_snapshot(
                include_dxdiag=include_dxdiag,
                elevate_sensors=elevate_sensors,
            )
            self._queue.put(("ok", snapshot))
        except Exception as exc:  # pragma: no cover - defensive
            self._queue.put(("error", exc))

    def _poll(self) -> None:
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._busy = False
            if kind == "ok":
                self.snapshot = payload
                self._layouts = list(payload.layouts)
                self._rebuild_tabs()
                stamp = payload.generated_at.strftime("%H:%M:%S")
                extra = (
                    s("status_warnings", count=len(payload.warnings)) if payload.warnings else ""
                )
                self._set_status(
                    s(
                        "status_collected",
                        time=stamp,
                        count=len(payload.sections),
                        extra=extra,
                        sensors=t(sensor_hub.status_note()),
                    ),
                    "ok",
                )
            else:
                self._set_status(s("status_error", error=payload), "error")
        self.after(120, self._poll)

    # ---------------------------------------------------------------------- tabs

    def _rebuild_tabs(self) -> None:
        for frame in self._tab_frames:
            frame.destroy()
        self._tab_frames.clear()
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        snapshot = self.snapshot
        if snapshot is None:
            return
        self._view = localize_snapshot(snapshot, self._language)

        summary_frame = ttk.Frame(self.notebook)
        self._tab_frames.append(summary_frame)
        self.notebook.add(summary_frame, text=s("summary_tab"))
        summary_tree = self._make_tree(
            summary_frame,
            columns=(s("col_parameter"), s("col_value")),
            widths=(360, 640),
            tree_heading=s("col_section"),
            tree_width=250,
        )
        for section in self._view.sections:
            node = summary_tree.insert(
                "", "end", text=section.title, values=("", ""), tags=("group",), open=True
            )
            for index, item in enumerate(section.summary):
                self._insert_item(summary_tree, node, item, index)

        for section in self._view.sections:
            frame = ttk.Frame(self.notebook)
            self._tab_frames.append(frame)
            self.notebook.add(frame, text=section.title)
            if section.key == "storage":
                self._add_layout_canvas(frame)
            tree = self._make_tree(
                frame,
                columns=(s("col_parameter"), s("col_value"), s("col_note")),
                widths=(300, 500, 200),
                tree_heading=s("col_group"),
                tree_width=240,
            )
            if section.summary:
                node = tree.insert(
                    "", "end", text=s("group_summary"), values=("", "", ""),
                    tags=("group",), open=True,
                )
                for index, item in enumerate(section.summary):
                    self._insert_item(tree, node, item, index)
            for group in section.groups:
                node = tree.insert(
                    "", "end", text=group.title, values=("", "", ""),
                    tags=("group",), open=True,
                )
                for index, item in enumerate(group.items):
                    self._insert_item(tree, node, item, index)

    def _make_tree(
        self,
        parent: ttk.Frame,
        columns: tuple[str, ...],
        widths: tuple[int, ...],
        tree_heading: str,
        tree_width: int,
    ) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="tree headings", selectmode="browse")
        tree.heading("#0", text=tree_heading)
        tree.column("#0", width=tree_width, minwidth=0, stretch=False)
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="w", stretch=column == columns[-1])
        tree.tag_configure("group", font=("Segoe UI Semibold", 9), foreground="#1f4f86",
                           background=GROUP_BG)
        tree.tag_configure("odd", background=ROW_ODD)
        tree.tag_configure("even", background=CARD)
        tree.tag_configure("sensitive", foreground=SENSITIVE)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def _insert_item(tree: ttk.Treeview, parent: str, item, index: int) -> None:
        tags = ["odd" if index % 2 else "even"]
        if item.sensitive:
            tags.append("sensitive")
        values: tuple[str, ...] = (item.label, item.value)
        if len(tree["columns"]) > 2:
            values += (item.note,)
        tree.insert(parent, "end", values=values, tags=tags)

    def _add_layout_canvas(self, frame: ttk.Frame) -> None:
        wrapper = ttk.Frame(frame)
        wrapper.pack(fill="x", padx=6, pady=(6, 0))
        canvas = tk.Canvas(
            wrapper,
            height=210,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.layout_canvas = canvas
        canvas.bind("<Configure>", lambda _event: self._draw_layouts())
        self.after(50, self._draw_layouts)

    def _draw_layouts(self) -> None:
        canvas = getattr(self, "layout_canvas", None)
        if canvas is None or not self._layouts:
            return
        try:
            if not canvas.winfo_exists():
                return
        except tk.TclError:
            return
        canvas.delete("all")
        width = canvas.winfo_width()
        if width < 60:
            return
        layouts = self._view.layouts if self._view is not None else self._layouts
        pad = 16
        bar_width = width - 2 * pad - 16
        y = 12
        for layout in layouts:
            canvas.create_text(
                pad, y, anchor="nw", text=layout.title,
                font=("Segoe UI Semibold", 9), fill="#1f4f86",
            )
            y += 21
            total = layout.total_size or 1
            x = pad
            for segment in layout.segments:
                seg_width = max(2, round(bar_width * segment.size / total))
                color = SEGMENT_COLORS.get(segment.kind, "#7a8a99")
                canvas.create_rectangle(x, y, x + seg_width, y + 18, fill=color, outline=CARD)
                if seg_width > 42:
                    canvas.create_text(
                        x + 4, y + 9, anchor="w", text=segment.label[:14],
                        fill="white", font=("Segoe UI", 8),
                    )
                x += seg_width
            y += 23
            legend = "    ".join(
                f"{segment.label}: {t(format_bytes(segment.size))}"
                + (
                    f" ({t('занято')} {t(format_bytes(segment.used))})"
                    if segment.used is not None
                    else ""
                )
                for segment in layout.segments
            )
            canvas.create_text(
                pad, y, anchor="nw", text=legend,
                font=("Segoe UI", 8), fill=MUTED,
            )
            y += 24
        canvas.configure(scrollregion=(0, 0, width, y + 10))

    # -------------------------------------------------------------------- export

    def export(self, fmt: str) -> None:
        if self.snapshot is None:
            messagebox.showwarning(s("error_title"), s("wait_collect"))
            return
        labels = {"txt": s("file_txt"), "json": s("file_json"), "md": s("file_md")}
        path = filedialog.asksaveasfilename(
            title=s("save_title"),
            defaultextension=f".{fmt}",
            initialfile=default_name(fmt),
            filetypes=[(labels.get(fmt, fmt), f"*.{fmt}"), (s("file_all"), "*.*")],
        )
        if not path:
            return
        try:
            save_snapshot(self.snapshot, path, fmt, self._redact.get(), self._language)
            self._set_status(s("status_saved", path=path), "ok")
        except Exception as exc:
            messagebox.showerror(s("error_title"), s("save_failed", error=exc))

    def screenshot(self) -> None:
        stamps = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title=s("save_as_title"),
            defaultextension=".png",
            initialfile=f"microspek_screen_{stamps}.png",
            filetypes=[(s("file_png"), "*.png"), (s("file_all"), "*.*")],
        )
        if not path:
            return
        self.after(250, lambda: self._grab_window(path))

    def _grab_window(self, path: str) -> None:
        try:
            from PIL import ImageGrab

            x, y = self.winfo_rootx(), self.winfo_rooty()
            width, height = self.winfo_width(), self.winfo_height()
            image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            image.save(path)
            self._set_status(s("status_screenshot", path=path), "ok")
        except Exception as exc:
            messagebox.showerror(s("error_title"), s("screenshot_failed", error=exc))


def run_gui(snapshot=None) -> None:
    """Create and run the GUI application."""
    app = MicroSpekApp(snapshot)
    app.mainloop()
