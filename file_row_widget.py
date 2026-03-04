import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path

from utils import get_row_config, update_row_fields

CARD_BG = "#ffffff"
F = ("Meiryo UI", 10)
FB = ("Meiryo UI", 10, "bold")
FS = ("Meiryo UI", 9)


def _btn(parent, text, cmd, bg="#6c757d", font_bold=False, px=10, py=4):
    f = FB if font_bold else F
    r = max(0, int(bg[1:3], 16) - 30)
    g = max(0, int(bg[3:5], 16) - 30)
    b = max(0, int(bg[5:7], 16) - 30)
    dark = f"#{r:02x}{g:02x}{b:02x}"
    return tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg="white", activebackground=dark, activeforeground="white",
        font=f, relief="flat", cursor="hand2", padx=px, pady=py,
    )


def _lbl(parent, text, bold=False, fg="#212529"):
    return tk.Label(parent, text=text, bg=CARD_BG, font=FB if bold else F,
                    fg=fg, anchor="w")


class FileRowWidget:
    def __init__(self, master, row_index, on_delete=None):
        self.row_index = row_index
        self.master = master
        self.on_delete = on_delete
        self._reload_job = None
        self._status_job = None

        conf = get_row_config(row_index)
        now = datetime.now()

        self.source_path = tk.StringVar(value=conf.get("source_path", ""))
        self.dest_path = tk.StringVar(value=conf.get("dest_path", ""))
        self.base_name = tk.StringVar(value=conf.get("base_name", ""))
        self.year = tk.StringVar(value=conf.get("year", str(now.year)))
        self.month = tk.StringVar(value=conf.get("month", f"{now.month:02}"))
        self.day = tk.StringVar(value=conf.get("day", f"{now.day:02}"))
        self.use_year = tk.BooleanVar(value=conf.get("use_year", True))
        self.use_month = tk.BooleanVar(value=conf.get("use_month", True))
        self.use_day = tk.BooleanVar(value=conf.get("use_day", False))
        self.use_underscores = tk.BooleanVar(value=conf.get("use_underscores", True))
        self.preview_name = tk.StringVar()

        saved = conf.get("selected_file_path", "")
        self.selected_file = saved if saved and os.path.exists(saved) else None

        self._build(now)
        self.update_preview()

        # フォルダが既に設定されている行だけポーリング開始
        if self.source_path.get() and os.path.isdir(self.source_path.get()):
            self.master.after_idle(self._start_poll)

    # ─── カード構築 ──────────────────────────────────────────────
    def _build(self, now):
        # ボーダー付きカード
        border = tk.Frame(self.master, bg="#c8cdd4")
        inner = tk.Frame(border, bg=CARD_BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.frame = border

        # カードヘッダー
        hdr = tk.Frame(inner, bg="#495057")
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"  行 {self.row_index + 1}",
                 bg="#495057", fg="white", font=FB, anchor="w", pady=6).pack(side="left")
        _btn(hdr, "× 削除", self._on_delete, bg="#dc3545", py=3).pack(
            side="right", padx=6, pady=4)

        # 2列ボディ
        body = tk.Frame(inner, bg=CARD_BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1, uniform="cols")
        body.columnconfigure(2, weight=1, uniform="cols")

        left = tk.Frame(body, bg=CARD_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 8), pady=12)
        left.columnconfigure(0, weight=1)

        # 縦区切り線
        tk.Frame(body, bg="#dee2e6", width=1).grid(
            row=0, column=1, sticky="ns", pady=8)

        right = tk.Frame(body, bg=CARD_BG)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 14), pady=12)
        right.columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right, now)

    # ─── 左列: 走査元フォルダ + ファイルリスト ──────────────────
    def _build_left(self, left):
        _lbl(left, "走査元フォルダ", bold=True).grid(row=0, column=0, sticky="w")

        src_row = tk.Frame(left, bg=CARD_BG)
        src_row.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        src_row.columnconfigure(1, weight=1)
        _btn(src_row, "フォルダ選択", self.choose_source, bg="#0d6efd").grid(row=0, column=0)
        ttk.Entry(src_row, textvariable=self.source_path, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(6, 0))

        # ファイルリスト
        list_frame = tk.Frame(left, bg="white", relief="solid", bd=1)
        list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        left.rowconfigure(2, weight=1)

        self.file_listbox = tk.Listbox(
            list_frame, font=F, bg="white", height=6,
            selectbackground="#0d6efd", selectforeground="white",
            activestyle="none", bd=0, highlightthickness=0,
            exportselection=False,
        )
        lb_scroll = ttk.Scrollbar(list_frame, orient="vertical",
                                   command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=lb_scroll.set)
        lb_scroll.pack(side="right", fill="y")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        # ファイル情報
        self.info_label = tk.Label(
            left, text="ファイルを選択してください",
            bg=CARD_BG, fg="#6c757d", font=FS,
            anchor="nw", justify="left", wraplength=300,
        )
        self.info_label.grid(row=3, column=0, sticky="ew")

    # ─── 右列: リネーム設定 + 移動先 ────────────────────────────
    def _build_right(self, right, now):
        # ベース名
        _lbl(right, "ベース名", bold=True).grid(row=0, column=0, sticky="w")
        base_entry = ttk.Entry(right, textvariable=self.base_name)
        base_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        base_entry.bind("<KeyRelease>", lambda e: self._on_base_name_change())

        # 日付オプション
        _lbl(right, "日付オプション", bold=True).grid(row=2, column=0, sticky="w")

        chk_frame = tk.Frame(right, bg=CARD_BG)
        chk_frame.grid(row=3, column=0, sticky="w", pady=(4, 2))
        for text, var in [("西暦", self.use_year), ("月", self.use_month), ("日", self.use_day)]:
            tk.Checkbutton(chk_frame, text=text, variable=var,
                           command=self._on_date_flag_change,
                           bg=CARD_BG, activebackground=CARD_BG, font=F).pack(
                side="left", padx=(0, 6))

        combo_frame = tk.Frame(right, bg=CARD_BG)
        combo_frame.grid(row=4, column=0, sticky="w", pady=(2, 8))
        ttk.Combobox(combo_frame, textvariable=self.year,
                     values=[str(y) for y in range(now.year - 5, now.year + 6)],
                     width=6, state="readonly").pack(side="left", padx=(0, 4))
        ttk.Combobox(combo_frame, textvariable=self.month,
                     values=[f"{m:02}" for m in range(1, 13)],
                     width=4, state="readonly").pack(side="left", padx=(0, 4))
        ttk.Combobox(combo_frame, textvariable=self.day,
                     values=[f"{d:02}" for d in range(1, 32)],
                     width=4, state="readonly").pack(side="left")

        self.year.trace_add("write", lambda *_: self._on_date_change())
        self.month.trace_add("write", lambda *_: self._on_date_change())
        self.day.trace_add("write", lambda *_: self._on_date_change())

        tk.Checkbutton(right, text="アンダーバー区切り",
                       variable=self.use_underscores,
                       command=self._on_underscore_change,
                       bg=CARD_BG, activebackground=CARD_BG, font=F).grid(
            row=5, column=0, sticky="w", pady=(0, 10))

        # プレビュー
        _lbl(right, "プレビュー", bold=True).grid(row=6, column=0, sticky="w")
        tk.Label(right, textvariable=self.preview_name,
                 bg=CARD_BG, fg="#0d6efd", font=FB, anchor="w", wraplength=300).grid(
            row=7, column=0, sticky="w", pady=(2, 12))

        # 区切り線
        tk.Frame(right, bg="#dee2e6", height=1).grid(
            row=8, column=0, sticky="ew", pady=(0, 10))

        # 移動先フォルダ
        _lbl(right, "移動先フォルダ", bold=True).grid(row=9, column=0, sticky="w")
        dest_row = tk.Frame(right, bg=CARD_BG)
        dest_row.grid(row=10, column=0, sticky="ew", pady=(4, 8))
        dest_row.columnconfigure(1, weight=1)
        _btn(dest_row, "フォルダ選択", self.choose_dest, bg="#6c757d").grid(row=0, column=0)
        ttk.Entry(dest_row, textvariable=self.dest_path, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(6, 0))

        # 実行
        exec_row = tk.Frame(right, bg=CARD_BG)
        exec_row.grid(row=11, column=0, sticky="w")
        _btn(exec_row, "  実行  ", self.execute, bg="#198754", font_bold=True, py=6).pack(
            side="left")
        self.status_label = tk.Label(exec_row, text="", bg=CARD_BG, font=F, fg="#198754")
        self.status_label.pack(side="left", padx=(10, 0))

    # ─── ライフサイクル ──────────────────────────────────────────
    def _on_delete(self):
        if self.on_delete:
            self.on_delete(self.row_index)

    def destroy(self):
        if self._reload_job:
            self.master.after_cancel(self._reload_job)
        if self._status_job:
            self.master.after_cancel(self._status_job)
        self.frame.destroy()

    # ─── ファイルリスト ──────────────────────────────────────────
    def _start_poll(self):
        self._update_file_list()
        self._reload_job = self.master.after(5000, self._start_poll)

    def _update_file_list(self):
        folder = self.source_path.get()
        if not os.path.isdir(folder):
            return
        try:
            with os.scandir(folder) as it:
                files = sorted(e.name for e in it if e.is_file())
        except OSError:
            return
        if list(self.file_listbox.get(0, tk.END)) != files:
            self.file_listbox.delete(0, tk.END)
            for f in files:
                self.file_listbox.insert(tk.END, f)

    def choose_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_path.set(folder)
            update_row_fields(self.row_index, source_path=folder)
            self._update_file_list()
            if not self._reload_job:
                self._start_poll()

    def choose_dest(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_path.set(folder)
            update_row_fields(self.row_index, dest_path=folder)

    def _on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        fname = self.file_listbox.get(sel[0])
        full = os.path.join(self.source_path.get(), fname)
        self.selected_file = full
        ext = Path(fname).suffix
        try:
            size = os.path.getsize(full)
            mtime = datetime.fromtimestamp(os.path.getmtime(full))
            info = f"{fname}\n{ext or '(拡張子なし)'}  ·  {size:,} bytes\n{mtime.strftime('%Y-%m-%d %H:%M')}"
        except OSError:
            info = fname
        self.info_label.config(text=info, fg="#343a40")
        update_row_fields(self.row_index,
                          selected_file_path=full,
                          selected_file_name=fname,
                          selected_file_ext=ext)
        self.update_preview()

    # ─── リネーム設定 ────────────────────────────────────────────
    def _on_base_name_change(self):
        update_row_fields(self.row_index, base_name=self.base_name.get())
        self.update_preview()

    def _on_date_change(self):
        update_row_fields(self.row_index,
                          year=self.year.get(),
                          month=self.month.get(),
                          day=self.day.get())
        self.update_preview()

    def _on_date_flag_change(self):
        update_row_fields(self.row_index,
                          use_year=self.use_year.get(),
                          use_month=self.use_month.get(),
                          use_day=self.use_day.get())
        self.update_preview()

    def _on_underscore_change(self):
        update_row_fields(self.row_index, use_underscores=self.use_underscores.get())
        self.update_preview()

    def update_preview(self):
        sep = "_" if self.use_underscores.get() else ""
        parts = []
        if self.use_year.get():
            parts.append(self.year.get())
        if self.use_month.get():
            parts.append(self.month.get())
        if self.use_day.get():
            parts.append(self.day.get())
        name = self.base_name.get()
        if parts:
            date_part = sep.join(parts)
            name = f"{name}{sep}{date_part}" if name else date_part
        ext = Path(self.selected_file).suffix if self.selected_file else ""
        self.preview_name.set(f"{name}{ext}" if (name or ext) else "（ベース名を入力してください）")

    # ─── 実行 ────────────────────────────────────────────────────
    def execute(self):
        if not self.selected_file or not os.path.exists(self.selected_file):
            self._show_status("⚠ ファイル未選択", "#dc3545")
            return
        if not self.dest_path.get():
            self._show_status("⚠ 移動先未選択", "#dc3545")
            return
        new_name = self.preview_name.get()
        if new_name == "（ベース名を入力してください）":
            self._show_status("⚠ ベース名を入力してください", "#dc3545")
            return
        dest_file = os.path.join(self.dest_path.get(), new_name)
        try:
            if os.path.exists(dest_file):
                if not messagebox.askyesno("確認", f"{new_name} は既に存在します。上書きしますか？"):
                    return
            os.rename(self.selected_file, dest_file)
            self.selected_file = None
            self._show_status("✔ 実行完了", "#198754")
            self._update_file_list()
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _show_status(self, msg, color="#198754"):
        self.status_label.config(text=msg, fg=color)
        if self._status_job:
            self.master.after_cancel(self._status_job)
        self._status_job = self.master.after(
            3000, lambda: self.status_label.config(text=""))
