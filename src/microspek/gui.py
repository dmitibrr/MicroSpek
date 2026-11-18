"""Tkinter GUI for MicroSpek."""

from __future__ import annotations

import queue
import threading
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .models import format_bytes
from .render import SEGMENT_COLORS, save_snapshot
from .snapshot import collect_snapshot


class MicroSpekApp(tk.Tk):
    """Main window with a summary tab, per-section tabs and disk layout canvas."""

    def __init__(self, snapshot=None) -> None:
        super().__init__()
        self.title("MicroSpek — характеристики ПК")
        self.geometry("1150x760")
        self.minsize(880, 560)

        self.snapshot = snapshot
        self._layouts = []
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        self._tab_frames: list[ttk.Frame] = []
        self.redact_var = tk.BooleanVar(value=False)
        self.dxdiag_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Готово к сбору")

        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()
        self.bind("<Control-r>", lambda _event: self.refresh())
        if snapshot is not None:
            self._layouts = list(snapshot.layouts)
            self._rebuild_tabs()
            self.status_var.set(f"Загружен слепок от {snapshot.generated_at.strftime('%H:%M:%S')}")
        else:
            self.refresh()
        self.after(150, self._poll)

    # ------------------------------------------------------------------ UI build

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=(0, 8))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=4)
        ttk.Button(bar, text="Слепок TXT", command=lambda: self.export("txt")).pack(side="left", padx=4)
        ttk.Button(bar, text="JSON", command=lambda: self.export("json")).pack(side="left", padx=4)
        ttk.Button(bar, text="PNG-отчёт", command=lambda: self.export("png")).pack(side="left", padx=4)
        ttk.Button(bar, text="Скриншот окна", command=self.screenshot).pack(side="left", padx=4)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=4)
        ttk.Checkbutton(bar, text="Скрывать чувствительное", variable=self.redact_var).pack(side="left", padx=4)
        ttk.Checkbutton(bar, text="dxdiag (медленно)", variable=self.dxdiag_var).pack(side="left", padx=4)

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 4))
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status_var, anchor="w").pack(fill="x")

    def _build_notebook(self) -> None:
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.notebook = ttk.Notebook(wrap)
        self.notebook.pack(fill="both", expand=True)

    @staticmethod
    def _make_tree(parent, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="tree headings", selectmode="browse")
        tree.heading("#0", text="")
        tree.column("#0", width=0, stretch=False)
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="w", stretch=column == columns[-1])
        tree.tag_configure("group", font=("Segoe UI", 9, "bold"), foreground="#12395e")
        tree.tag_configure("sensitive", foreground="#9b5318")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return tree

    # ---------------------------------------------------------------- collection

    def refresh(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.status_var.set("Сбор данных…")
        threading.Thread(
            target=self._worker, args=(self.dxdiag_var.get(),), daemon=True
        ).start()

    def _worker(self, include_dxdiag: bool) -> None:
        try:
            self._queue.put(("ok", collect_snapshot(include_dxdiag=include_dxdiag)))
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
                extra = f", предупреждений: {len(payload.warnings)}" if payload.warnings else ""
                self.status_var.set(f"Обновлено {stamp} · разделов: {len(payload.sections)}{extra}")
            else:
                self.status_var.set(f"Ошибка сбора: {payload}")
        self.after(150, self._poll)

    # ---------------------------------------------------------------------- tabs

    def _rebuild_tabs(self) -> None:
        for frame in self._tab_frames:
            frame.destroy()
        self._tab_frames.clear()

        snapshot = self.snapshot
        if snapshot is None:
            return

        summary_frame = ttk.Frame(self.notebook)
        self._tab_frames.append(summary_frame)
        self.notebook.add(summary_frame, text="Сводка")
        summary_tree = self._make_tree(summary_frame, ("Раздел", "Параметр", "Значение"), (200, 220, 620))
        for section in snapshot.sections:
            for item in section.summary:
                tags = ("sensitive",) if item.sensitive else ()
                summary_tree.insert("", "end", values=(section.title, item.label, item.value), tags=tags)

        for section in snapshot.sections:
            frame = ttk.Frame(self.notebook)
            self._tab_frames.append(frame)
            self.notebook.add(frame, text=section.title)
            if section.key == "storage":
                self._add_layout_canvas(frame)
            tree = self._make_tree(frame, ("Параметр", "Значение", "Примечание"), (280, 520, 200))
            if section.summary:
                node = tree.insert("", "end", text="Сводка", values=("", "", ""), tags=("group",))
                for item in section.summary:
                    self._insert_item(tree, node, item)
            for group in section.groups:
                node = tree.insert("", "end", text=group.title, values=("", "", ""), tags=("group",))
                for item in group.items:
                    self._insert_item(tree, node, item)
                tree.item(node, open=True)

    @staticmethod
    def _insert_item(tree: ttk.Treeview, parent: str, item) -> None:
        tags = ("sensitive",) if item.sensitive else ()
        tree.insert(parent, "end", values=(item.label, item.value, item.note), tags=tags)

    def _add_layout_canvas(self, frame: ttk.Frame) -> None:
        wrapper = ttk.Frame(frame)
        wrapper.pack(fill="x", padx=6, pady=6)
        canvas = tk.Canvas(
            wrapper,
            height=210,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#c8d0d8",
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
        canvas.delete("all")
        width = canvas.winfo_width()
        if width < 60:
            return
        pad = 14
        bar_width = width - 2 * pad - 16
        y = 10
        for layout in self._layouts:
            canvas.create_text(
                pad, y, anchor="nw", text=layout.title,
                font=("Segoe UI", 9, "bold"), fill="#12395e",
            )
            y += 20
            total = layout.total_size or 1
            x = pad
            for segment in layout.segments:
                seg_width = max(2, round(bar_width * segment.size / total))
                color = SEGMENT_COLORS.get(segment.kind, "#7a8a99")
                canvas.create_rectangle(x, y, x + seg_width, y + 18, fill=color, outline="white")
                if seg_width > 42:
                    canvas.create_text(
                        x + 3, y + 9, anchor="w", text=segment.label[:12],
                        fill="white", font=("Segoe UI", 8),
                    )
                x += seg_width
            y += 22
            legend = "   ".join(
                f"{segment.label}: {format_bytes(segment.size)}"
                + (f" (занято {format_bytes(segment.used)})" if segment.used is not None else "")
                for segment in layout.segments
            )
            canvas.create_text(
                pad, y, anchor="nw", text=legend,
                font=("Segoe UI", 8), fill="#546274",
            )
            y += 22
        canvas.configure(scrollregion=(0, 0, width, y + 10))

    # -------------------------------------------------------------------- export

    def export(self, fmt: str) -> None:
        if self.snapshot is None:
            messagebox.showwarning("MicroSpek", "Сначала дождитесь окончания сбора данных.")
            return
        extensions = {"txt": "Текстовый слепок (*.txt)", "json": "JSON (*.json)", "png": "PNG (*.png)"}
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial = f"microspek_{'snapshot' if fmt == 'txt' else 'report'}_{stamp}.{fmt}"
        path = filedialog.asksaveasfilename(
            title="Сохранить отчёт",
            defaultextension=f".{fmt}",
            initialfile=initial,
            filetypes=[(extensions.get(fmt, fmt), f"*.{fmt}"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            save_snapshot(self.snapshot, path, fmt, self.redact_var.get())
            self.status_var.set(f"Сохранено: {path}")
        except Exception as exc:
            messagebox.showerror("MicroSpek", f"Не удалось сохранить:\n{exc}")

    def screenshot(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Сохранить скриншот окна",
            defaultextension=".png",
            initialfile=f"microspek_screen_{stamp}.png",
            filetypes=[("PNG (*.png)", "*.png"), ("Все файлы", "*.*")],
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
            self.status_var.set(f"Скриншот сохранён: {path}")
        except Exception as exc:
            messagebox.showerror("MicroSpek", f"Не удалось сделать скриншот:\n{exc}")


def run_gui(snapshot=None) -> None:
    """Create and run the GUI application."""
    app = MicroSpekApp(snapshot)
    app.mainloop()
