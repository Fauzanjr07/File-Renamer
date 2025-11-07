#!/usr/bin/env python3
"""
Simple Tkinter GUI for batch-renaming selected files with a sequence placeholder.

Features:
- Pick multiple files (open file dialog)
- Pattern supports either a literal "-n" token which will be replaced by the sequence number,
  or a Python-format placeholder `{n}` / `{n:03d}` for padding control.
- Start value and padding controls
- Preview the planned mapping
- Perform renames (collision-safe) and optionally save a mapping CSV

Run:
  python gui_rename.py

This is a minimal, dependency-free GUI using the Python standard library (Tkinter).
"""

from __future__ import annotations

import csv
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Optional colorful modern theming with ttkbootstrap if installed
USE_TTKB = False
try:
    import ttkbootstrap as tb  # type: ignore
    USE_TTKB = True
except Exception:
    tb = None  # type: ignore
from typing import List, Tuple


def next_free_name(directory: str, candidate: str) -> str:
    base, ext = os.path.splitext(candidate)
    path = os.path.join(directory, candidate)
    if not os.path.exists(path):
        return candidate
    i = 1
    while True:
        newname = f"{base}_{i}{ext}"
        if not os.path.exists(os.path.join(directory, newname)):
            return newname
        i += 1


def render_name(pattern: str, n: int, src_ext: str) -> str:
    """Render a name for sequence index n.

    - If pattern contains '{n', use pattern.format(n=n).
    - Else replace literal '-n' with n (optionally zero-padded using padding supplied elsewhere).
    - If resulting name has no extension, append src_ext.
    """
    name = pattern
    if "{n" in pattern:
        try:
            name = pattern.format(n=n)
        except Exception:
            name = pattern.replace("-n", str(n))
    elif "-n" in pattern:
        name = pattern.replace("-n", str(n))
    else:
        # fallback: append number
        name = f"{pattern}{n}"

    base, ext = os.path.splitext(name)
    if not ext:
        name = name + src_ext
    return name


class GuiRenamer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Batch Image Renamer")
        # set a friendly default size
        self.geometry("900x620")

        # Modernize look with optional ttkbootstrap; fallback to built-in ttk styles
        if USE_TTKB:
            # Choose a colorful, modern theme; user can change from UI
            self.style = tb.Style(theme='flatly')
            self.available_themes = list(self.style.theme_names())
        else:
            self.style = ttk.Style()
            try:
                self.style.theme_use('clam')
            except Exception:
                pass
        # Common stylistic tweaks
        self.style.configure('.', font=('Segoe UI', 10))
        self.style.configure('TButton', padding=(8, 6))
        self.style.configure('TEntry', padding=(6, 4))
        # Header label style
        try:
            self.style.configure('Header.TLabel', font=('Segoe UI', 10), foreground="#00050a")
        except Exception:
            pass
        # Accent button style if ttkbootstrap available
        self.primary_button_style = 'Accent.TButton' if USE_TTKB else 'TButton'

        self.files: List[str] = []

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Top-left header with author and version
        header_row = ttk.Frame(frm)
        header_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header_row, text="Author: N4co  •  Version: 1.0", style='Header.TLabel').pack(side=tk.LEFT)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="Add Files", command=self.add_files).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Add Folder", command=self.add_folder).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(btn_row, text="Clear", command=self.clear_files).pack(side=tk.LEFT, padx=(6,0))
        # Recursive checkbox
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(btn_row, text="Recursive (folders)", variable=self.recursive_var).pack(side=tk.LEFT, padx=(12,0))

        pattern_row = ttk.Frame(frm)
        pattern_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(pattern_row, text="Pattern (use -n or {n}):").pack(side=tk.LEFT)
        self.pattern_var = tk.StringVar(value="test_board_-n")
        ttk.Entry(pattern_row, textvariable=self.pattern_var, width=40).pack(side=tk.LEFT, padx=(6, 10))

        ttk.Label(pattern_row, text="Start:").pack(side=tk.LEFT)
        self.start_var = tk.IntVar(value=1)
        ttk.Entry(pattern_row, textvariable=self.start_var, width=6).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(pattern_row, text="Padding:").pack(side=tk.LEFT)
        self.padding_var = tk.IntVar(value=3)
        ttk.Entry(pattern_row, textvariable=self.padding_var, width=6).pack(side=tk.LEFT, padx=(4, 10))

        # Add a dropdown to control sorting (name or mtime) for folder imports
        ttk.Label(pattern_row, text="Sort: ").pack(side=tk.LEFT, padx=(12,0))
        self.sort_var = tk.StringVar(value='name')
        ttk.Combobox(pattern_row, textvariable=self.sort_var, values=('name','mtime'), width=8, state='readonly').pack(side=tk.LEFT, padx=(4,0))

        list_row = ttk.Frame(frm)
        list_row.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.listbox = tk.Listbox(list_row, selectmode=tk.EXTENDED, activestyle='dotbox')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        right_col = ttk.Frame(list_row, width=320)
        right_col.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

        ttk.Button(right_col, text="Preview", style=self.primary_button_style, command=self.preview).pack(fill=tk.X, pady=(0,6))
        ttk.Button(right_col, text="Rename", style=self.primary_button_style, command=self.rename).pack(fill=tk.X, pady=(0,6))
        ttk.Button(right_col, text="Export mapping CSV", command=self.export_csv).pack(fill=tk.X, pady=(0,6))
        ttk.Button(right_col, text="Select All", command=lambda: self.listbox.select_set(0, tk.END)).pack(fill=tk.X, pady=(6,0))
        ttk.Button(right_col, text="Deselect", command=lambda: self.listbox.select_clear(0, tk.END)).pack(fill=tk.X, pady=(6,0))

        # Preview text box with thicker border/outline
        self.preview_text = tk.Text(
            frm,
            height=12,
            bd=20,                 # thicker border
            relief="solid",       # solid border style
            highlightthickness=10, # outer highlight line thickness
            highlightbackground="#000000",  # outline color (inactive)
            highlightcolor="#08111B",       # outline color (active)
        )
        self.preview_text.pack(fill=tk.BOTH, expand=False, pady=(8, 0))

        # Theme selector (only when ttkbootstrap is available)
        if USE_TTKB:
            theme_row = ttk.Frame(frm)
            theme_row.pack(fill=tk.X, pady=(8,0))
            ttk.Label(theme_row, text="Theme:").pack(side=tk.LEFT)
            self.theme_var = tk.StringVar(value=self.style.theme.name)
            self.theme_combo = ttk.Combobox(theme_row, textvariable=self.theme_var, values=self.available_themes, width=18, state='readonly')
            self.theme_combo.pack(side=tk.LEFT, padx=(6,10))
            ttk.Button(theme_row, text="Apply Theme", command=self._apply_theme).pack(side=tk.LEFT)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Select files to rename", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"), ("All files", "*.*")])
        if not paths:
            return
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, os.path.basename(p))

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing files")
        if not folder:
            return
        recursive = self.recursive_var.get()
        exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        collected = []
        if recursive:
            for root, _, files in os.walk(folder):
                for fn in files:
                    if fn.lower().endswith(exts):
                        collected.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(folder):
                full = os.path.join(folder, fn)
                if os.path.isfile(full) and fn.lower().endswith(exts):
                    collected.append(full)

        # optional sort
        if self.sort_var.get() == 'mtime':
            collected.sort(key=lambda p: os.path.getmtime(p))
        else:
            # natural-like sort by filename
            collected.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", os.path.basename(s))])

        for p in collected:
            if p not in self.files:
                self.files.append(p)
                display = os.path.relpath(p)
                self.listbox.insert(tk.END, display)

    def clear_files(self) -> None:
        self.files = []
        self.listbox.delete(0, tk.END)
        self.preview_text.delete("1.0", tk.END)

    def _build_actions(self) -> List[Tuple[str, str]]:
        pattern = self.pattern_var.get().strip()
        start = int(self.start_var.get())
        padding = int(self.padding_var.get() or 0)
        actions: List[Tuple[str, str]] = []
        n = start
        for src in self.files:
            _, ext = os.path.splitext(src)
            # If pattern uses -n literal and padding>0, apply zero pad to the number
            if "-n" in pattern and padding:
                num = str(n).zfill(padding)
                target_base = pattern.replace("-n", num)
                name = target_base
            else:
                # render_name will append ext if missing
                name = render_name(pattern, n, ext)

            # Ensure extension present
            base, ext2 = os.path.splitext(name)
            if not ext2:
                name = name + ext

            name = next_free_name(os.path.dirname(src), name)
            dst = os.path.join(os.path.dirname(src), name)
            actions.append((src, dst))
            n += 1
        return actions

    def preview(self) -> None:
        self.preview_text.delete("1.0", tk.END)
        if not self.files:
            messagebox.showinfo("No files", "Please add files first")
            return
        actions = self._build_actions()
        for src, dst in actions:
            self.preview_text.insert(tk.END, f"{os.path.basename(src)} -> {os.path.basename(dst)}\n")

    def rename(self) -> None:
        if not self.files:
            messagebox.showinfo("No files", "Please add files first")
            return
        actions = self._build_actions()
        confirm = messagebox.askyesno("Confirm", f"Rename {len(actions)} files? This cannot be undone from the GUI.")
        if not confirm:
            return
        failed = []
        for src, dst in actions:
            try:
                os.rename(src, dst)
            except Exception as e:
                failed.append((src, dst, str(e)))
        if failed:
            msg = "Some renames failed:\n" + "\n".join([f"{os.path.basename(s)} -> {os.path.basename(d)}: {e}" for s, d, e in failed])
            messagebox.showerror("Failed", msg)
        else:
            messagebox.showinfo("Done", f"Renamed {len(actions)} files")
        # Refresh list to show new basenames
        self.files = [dst for _, dst in actions if os.path.exists(dst)]
        self.listbox.delete(0, tk.END)
        for p in self.files:
            self.listbox.insert(tk.END, os.path.basename(p))
        self.preview()

    def export_csv(self) -> None:
        if not self.files:
            messagebox.showinfo("No files", "Please add files first")
            return
        actions = self._build_actions()
        path = filedialog.asksaveasfilename(title="Save mapping CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["name_raw", "name_change"])
                for src, dst in actions:
                    w.writerow([os.path.basename(src), os.path.basename(dst)])
            messagebox.showinfo("Saved", f"Mapping saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write CSV: {e}")

    def _apply_theme(self) -> None:
        if not USE_TTKB:
            messagebox.showinfo("Theme", "Extra colorful themes require 'ttkbootstrap'. Install with: pip install ttkbootstrap")
            return
        try:
            chosen = self.theme_var.get()
            self.style.theme_use(chosen)
        except Exception as e:
            messagebox.showerror("Theme", f"Failed to apply theme: {e}")


def main() -> None:
    app = GuiRenamer()
    app.mainloop()


if __name__ == "__main__":
    main()
