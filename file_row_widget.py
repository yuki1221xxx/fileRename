import os
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from datetime import datetime
from pathlib import Path
from utils import get_row_config, update_row_fields


class FileRowWidget:
    def __init__(self, master, row_index, on_delete=None):
        self.row_index = row_index
        self.row_key = f"row{row_index}"
        self.master = master
        self.on_delete = on_delete

        row_conf = get_row_config(row_index)
        now = datetime.now()

        self.source_path = tk.StringVar(value=row_conf.get("source_path", ""))
        self.dest_path = tk.StringVar(value=row_conf.get("dest_path", ""))
        self.base_name = tk.StringVar(value=row_conf.get("base_name", ""))

        self.year = tk.StringVar(value=row_conf.get("year", str(now.year)))
        self.month = tk.StringVar(value=row_conf.get("month", f"{now.month:02}"))
        self.day = tk.StringVar(value=row_conf.get("day", f"{now.day:02}"))

        # 個別日付チェック
        self.use_year = tk.BooleanVar(value=row_conf.get("use_year", True))
        self.use_month = tk.BooleanVar(value=row_conf.get("use_month", True))
        self.use_day = tk.BooleanVar(value=row_conf.get("use_day", False))

        self.use_underscores = tk.BooleanVar(value=row_conf.get("use_underscores", True))

        saved_selected = row_conf.get("selected_file_path", "")
        self.selected_file = saved_selected if saved_selected and os.path.exists(saved_selected) else None

        self.preview_name = tk.StringVar()
        self.status_after_id = None
        self._reload_job = None

        self._build_row()
        # Defer the first reload until the UI is idle so startup feels lighter.
        self.master.after_idle(self._start_auto_reload)
        self.update_preview_name()

    # ===== UI build =====
    def _build_row(self):
        card = tb.Frame(self.master, bootstyle="light", borderwidth=2, relief="ridge", padding=8)
        self.card = card
        card.grid(row=self.row_index, column=0, sticky="nsew", padx=5, pady=5)
        self.master.columnconfigure(0, weight=1)

        for i in range(4):
            card.columnconfigure(i, weight=1, uniform="cardcols")
        card.columnconfigure(4, weight=0)

        del_btn = tb.Button(card, text="×", width=3, bootstyle="danger", command=self._on_delete_clicked)
        del_btn.grid(row=0, column=4, sticky="ne", padx=(4, 0), pady=(0, 4))

        # ① 走査元
        source_frame = tb.Labelframe(card, text="① 走査元フォルダ", bootstyle="secondary")
        source_frame.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        source_frame.columnconfigure(1, weight=1)
        source_frame.rowconfigure(2, weight=1)

        tb.Button(source_frame, text="フォルダ選択", bootstyle="primary", command=self.choose_source_folder)\
            .grid(row=0, column=0, sticky="w", pady=2)
        tb.Entry(source_frame, textvariable=self.source_path, state="readonly")\
            .grid(row=0, column=1, sticky="ew", padx=5)

        self.file_listbox = tk.Listbox(source_frame, height=6, exportselection=False, font=("Meiryo UI", 11))
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # ② ファイル情報
        info_frame = tb.Labelframe(card, text="② ファイル情報", bootstyle="info")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        info_frame.columnconfigure(0, weight=1)
        self.info_label = tb.Label(
            info_frame,
            text="ファイル情報がここに表示されます",
            anchor="nw",
            justify="left",
            wraplength=260,
        )
        self.info_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # ③ リネーム設定
        rename_frame = tb.Labelframe(card, text="③ リネーム設定", bootstyle="success")
        rename_frame.grid(row=0, column=2, sticky="nsew", padx=3, pady=3)
        rename_frame.columnconfigure(0, weight=1)

        tb.Label(rename_frame, text="ベース名").grid(row=0, column=0, sticky="w")
        base_entry = tb.Entry(rename_frame, textvariable=self.base_name)
        base_entry.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        base_entry.bind("<KeyRelease>", lambda e: self._on_base_name_change())

        tb.Label(rename_frame, text="プレビュー:").grid(row=2, column=0, sticky="w")
        tb.Label(
            rename_frame,
            textvariable=self.preview_name,
            bootstyle="info",
            anchor="w",
            justify="left",
            wraplength=240,
        ).grid(row=3, column=0, sticky="w", pady=(0, 6))

        # ---- 新チェックボックス群 ----
        date_frame = tb.Labelframe(rename_frame, text="日付要素", bootstyle="secondary")
        date_frame.grid(row=4, column=0, sticky="w", pady=3)

        tb.Checkbutton(date_frame, text="西暦", variable=self.use_year,
                       command=self._on_date_flag_change).pack(side="left", padx=(0, 5))
        tb.Checkbutton(date_frame, text="月", variable=self.use_month,
                       command=self._on_date_flag_change).pack(side="left", padx=(0, 5))
        tb.Checkbutton(date_frame, text="日", variable=self.use_day,
                       command=self._on_date_flag_change).pack(side="left", padx=(0, 5))

        combo_frame = tb.Frame(rename_frame)
        combo_frame.grid(row=5, column=0, sticky="w", pady=3)
        tb.Combobox(
            combo_frame,
            textvariable=self.year,
            values=[str(y) for y in range(datetime.now().year - 5, datetime.now().year + 6)],
            width=6,
            state="readonly"
        ).pack(side="left", padx=(0, 3))
        tb.Combobox(
            combo_frame,
            textvariable=self.month,
            values=[f"{m:02}" for m in range(1, 13)],
            width=4,
            state="readonly"
        ).pack(side="left", padx=(0, 3))
        tb.Combobox(
            combo_frame,
            textvariable=self.day,
            values=[f"{d:02}" for d in range(1, 32)],
            width=4,
            state="readonly"
        ).pack(side="left")

        self.year.trace_add("write", lambda *_: self._on_date_change())
        self.month.trace_add("write", lambda *_: self._on_date_change())
        self.day.trace_add("write", lambda *_: self._on_date_change())

        tb.Checkbutton(rename_frame, text="区切りにアンダーバーを使用",
                       variable=self.use_underscores, command=self._on_underscore_change)\
            .grid(row=6, column=0, sticky="w", pady=(4, 0))

        # ④ 移動先 & 実行
        action_frame = tb.Labelframe(card, text="④ 移動先 & 実行", bootstyle="warning")
        action_frame.grid(row=0, column=3, sticky="nsew", padx=3, pady=3)
        action_frame.columnconfigure(0, weight=1)
        tb.Button(action_frame, text="移動先選択", command=self.choose_dest_folder)\
            .grid(row=0, column=0, sticky="w", pady=(0, 3))
        tb.Entry(action_frame, textvariable=self.dest_path, state="readonly")\
            .grid(row=1, column=0, sticky="ew", pady=(0, 5))
        btn_row = tb.Frame(action_frame)
        btn_row.grid(row=2, column=0, sticky="w")
        tb.Button(btn_row, text="実行", bootstyle="success", command=self.execute)\
            .pack(side="left", padx=(0, 5))
        self.status_label = tb.Label(btn_row, text="", bootstyle="success")
        self.status_label.pack(side="left")

    # ===== 基本動作 =====
    def _on_delete_clicked(self):
        if self.on_delete:
            self.on_delete(self.row_index)

    def destroy(self):
        if self._reload_job:
            self.master.after_cancel(self._reload_job)
        self.card.destroy()

    def show_status(self, message, style="success"):
        self.status_label.config(text=message, bootstyle=style)
        if self.status_after_id:
            self.master.after_cancel(self.status_after_id)
        self.status_after_id = self.master.after(3000, lambda: self.status_label.config(text=""))

    def choose_source_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_path.set(folder)
            update_row_fields(self.row_index, source_path=folder)
            self._update_file_list()

    def choose_dest_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_path.set(folder)
            update_row_fields(self.row_index, dest_path=folder)

    def _start_auto_reload(self):
        self._update_file_list()
        self._reload_job = self.master.after(3000, self._start_auto_reload)

    def _update_file_list(self):
        folder = self.source_path.get()
        if not os.path.isdir(folder):
            return
        try:
            with os.scandir(folder) as entries:
                current_files = sorted(entry.name for entry in entries if entry.is_file())
        except OSError:
            return
        displayed = list(self.file_listbox.get(0, tk.END))
        if current_files != displayed:
            self.file_listbox.delete(0, tk.END)
            for f in current_files:
                self.file_listbox.insert(tk.END, f)

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        filename = self.file_listbox.get(sel[0])
        full_path = os.path.join(self.source_path.get(), filename)
        self.selected_file = full_path
        ext = Path(filename).suffix
        size = os.path.getsize(full_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(full_path))
        info = (
            f"{filename}\n拡張子: {ext}\nサイズ: {size:,} bytes\n更新日時: {mod_time.strftime('%Y-%m-%d %H:%M')}"
        )
        self.info_label.config(text=info)
        update_row_fields(
            self.row_index,
            selected_file_path=full_path,
            selected_file_name=filename,
            selected_file_ext=ext,
            selected_file_size=size,
            selected_file_mtime=mod_time.isoformat(),
        )
        self.update_preview_name()

    def _on_base_name_change(self):
        update_row_fields(self.row_index, base_name=self.base_name.get())
        self.update_preview_name()

    def _on_date_change(self):
        update_row_fields(self.row_index,
                          year=self.year.get(), month=self.month.get(), day=self.day.get())
        self.update_preview_name()

    def _on_date_flag_change(self):
        update_row_fields(self.row_index,
                          use_year=self.use_year.get(),
                          use_month=self.use_month.get(),
                          use_day=self.use_day.get())
        self.update_preview_name()

    def _on_underscore_change(self):
        update_row_fields(self.row_index, use_underscores=self.use_underscores.get())
        self.update_preview_name()

    def update_preview_name(self):
        name = self.base_name.get()
        sep = "_" if self.use_underscores.get() else ""

        parts = []
        if self.use_year.get():
            parts.append(self.year.get())
        if self.use_month.get():
            parts.append(self.month.get())
        if self.use_day.get():
            parts.append(self.day.get())

        if parts:
            date_part = sep.join(parts)
            name = f"{name}{sep}{date_part}" if name else date_part

        ext = Path(self.selected_file).suffix if self.selected_file else ""
        self.preview_name.set(f"{name}{ext}")

    def execute(self):
        if not self.selected_file:
            self.show_status("⚠ ファイル未選択", style="danger")
            return
        if not self.dest_path.get():
            self.show_status("⚠ 移動先未選択", style="danger")
            return
        new_name = self.preview_name.get()
        dest_file = os.path.join(self.dest_path.get(), new_name)
        try:
            if os.path.exists(dest_file):
                overwrite = messagebox.askyesno("確認", f"{new_name} は既に存在します。上書きしますか？")
                if not overwrite:
                    return
            os.rename(self.selected_file, dest_file)
            self.show_status("✔ 実行完了", style="success")
        except Exception as e:
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
