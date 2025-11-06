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

        # ここでその時点のrowだけ読む（他の行は読み込まない）
        row_conf = get_row_config(row_index)
        now = datetime.now()

        self.source_path = tk.StringVar(value=row_conf.get("source_path", ""))
        self.dest_path = tk.StringVar(value=row_conf.get("dest_path", ""))
        self.base_name = tk.StringVar(value=row_conf.get("base_name", ""))

        self.year = tk.StringVar(value=row_conf.get("year", str(now.year)))
        self.month = tk.StringVar(value=row_conf.get("month", f"{now.month:02}"))
        self.use_date = tk.BooleanVar(value=row_conf.get("use_date", True))
        self.use_underscores = tk.BooleanVar(value=row_conf.get("use_underscores", True))

        saved_selected = row_conf.get("selected_file_path", "")
        self.selected_file = saved_selected if saved_selected and os.path.exists(saved_selected) else None

        self.preview_name = tk.StringVar()
        self.status_after_id = None

        self._build_row()
        self._start_auto_reload()
        self.update_preview_name()

        if os.path.isdir(self.source_path.get()):
            self._update_file_list()

    # ===== UI build =====
    def _build_row(self):
        card = tb.Frame(self.master, bootstyle="light", borderwidth=2, relief="ridge", padding=5)
        self.card = card
        card.grid(row=self.row_index, column=0, sticky="nsew", padx=5, pady=5)
        self.master.columnconfigure(0, weight=1)

        # 0..3: 内容, 4: 削除ボタン
        for i in range(4):
            card.columnconfigure(i, weight=1)
        card.columnconfigure(4, weight=0)

        # 削除ボタン
        del_btn = tb.Button(card, text="×", width=3, bootstyle="danger", command=self._on_delete_clicked)
        del_btn.grid(row=0, column=4, sticky="ne", padx=(4, 0), pady=(0, 4))

        # ① 走査元
        source_frame = tb.Labelframe(card, text="① 走査元フォルダ", bootstyle="secondary")
        source_frame.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        source_frame.columnconfigure(0, weight=0)
        source_frame.columnconfigure(1, weight=1)
        source_frame.rowconfigure(2, weight=1)

        tb.Button(source_frame, text="フォルダ選択", bootstyle="primary", command=self.choose_source_folder) \
            .grid(row=0, column=0, sticky="w", pady=2)
        tb.Entry(source_frame, textvariable=self.source_path, state="readonly") \
            .grid(row=0, column=1, sticky="ew", padx=5)

        self.file_listbox = tk.Listbox(source_frame, height=4, exportselection=False)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # ② ファイル情報
        info_frame = tb.Labelframe(card, text="② ファイル情報", bootstyle="info")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)

        self.info_label = tb.Label(info_frame, text="ファイル情報がここに表示されます", anchor="nw", justify="left")
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
        tb.Label(rename_frame, textvariable=self.preview_name, bootstyle="info", anchor="w", justify="left") \
            .grid(row=3, column=0, sticky="w", pady=(0, 6))

        tb.Checkbutton(rename_frame, text="日付を付加する", variable=self.use_date, command=self._on_use_date_change) \
            .grid(row=4, column=0, sticky="w")

        date_frame = tb.Frame(rename_frame)
        date_frame.grid(row=5, column=0, sticky="w", pady=3)
        tb.Combobox(
            date_frame,
            textvariable=self.year,
            values=[str(y) for y in range(datetime.now().year - 5, datetime.now().year + 6)],
            width=6,
            state="readonly"
        ).pack(side="left", padx=(0, 3))
        tb.Combobox(
            date_frame,
            textvariable=self.month,
            values=[f"{m:02}" for m in range(1, 13)],
            width=4,
            state="readonly"
        ).pack(side="left", padx=(0, 3))

        self.year.trace_add("write", lambda *_: self._on_date_change())
        self.month.trace_add("write", lambda *_: self._on_date_change())

        tb.Checkbutton(rename_frame, text="区切りにアンダーバーを使用",
                       variable=self.use_underscores, command=self._on_underscore_change) \
            .grid(row=6, column=0, sticky="w", pady=(4, 0))

        # ④ 移動先 & 実行
        action_frame = tb.Labelframe(card, text="④ 移動先 & 実行", bootstyle="warning")
        action_frame.grid(row=0, column=3, sticky="nsew", padx=3, pady=3)
        action_frame.columnconfigure(0, weight=1)

        tb.Button(action_frame, text="移動先選択", command=self.choose_dest_folder) \
            .grid(row=0, column=0, sticky="w", pady=(0, 3))
        tb.Entry(action_frame, textvariable=self.dest_path, state="readonly") \
            .grid(row=1, column=0, sticky="ew", pady=(0, 5))

        btn_row = tb.Frame(action_frame)
        btn_row.grid(row=2, column=0, sticky="w")
        tb.Button(btn_row, text="実行", bootstyle="success", command=self.execute) \
            .pack(side="left", padx=(0, 5))
        self.status_label = tb.Label(btn_row, text="", bootstyle="success")
        self.status_label.pack(side="left")

    # ===== 削除ボタン =====
    def _on_delete_clicked(self):
        if self.on_delete:
            self.on_delete(self.row_index)

    def destroy(self):
        self.card.destroy()

    # ===== ステータス表示 =====
    def show_status(self, message, style="success"):
        self.status_label.config(text=message, bootstyle=style)
        if self.status_after_id:
            self.master.after_cancel(self.status_after_id)
        self.status_after_id = self.master.after(3000, lambda: self.status_label.config(text=""))

    # ===== フォルダ選択 =====
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

    # ===== 自動リロード =====
    def _start_auto_reload(self):
        self._update_file_list()
        self.master.after(3000, self._start_auto_reload)

    def _update_file_list(self):
        folder = self.source_path.get()
        if not os.path.isdir(folder):
            return
        current_files = sorted(
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        )
        displayed = list(self.file_listbox.get(0, tk.END))
        if current_files != displayed:
            self.file_listbox.delete(0, tk.END)
            for f in current_files:
                self.file_listbox.insert(tk.END, f)

    # ===== ファイル選択 =====
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
            f"{filename}\n"
            f"拡張子: {ext}\n"
            f"サイズ: {size:,} bytes\n"
            f"更新日時: {mod_time.strftime('%Y-%m-%d %H:%M')}"
        )
        self.info_label.config(text=info)

        # まとめて保存（この行だけ上書き）
        update_row_fields(
            self.row_index,
            selected_file_path=full_path,
            selected_file_name=filename,
            selected_file_ext=ext,
            selected_file_size=size,
            selected_file_mtime=mod_time.isoformat(),
        )

        self.update_preview_name()

    # ===== 各種変更 =====
    def _on_base_name_change(self):
        update_row_fields(self.row_index, base_name=self.base_name.get())
        self.update_preview_name()

    def _on_date_change(self):
        update_row_fields(self.row_index, year=self.year.get(), month=self.month.get())
        self.update_preview_name()

    def _on_use_date_change(self):
        update_row_fields(self.row_index, use_date=self.use_date.get())
        self.update_preview_name()

    def _on_underscore_change(self):
        update_row_fields(self.row_index, use_underscores=self.use_underscores.get())
        self.update_preview_name()

    # ===== プレビュー更新 =====
    def update_preview_name(self):
        name = self.base_name.get()
        sep = "_" if self.use_underscores.get() else ""
        if self.use_date.get():
            date_part = sep.join([self.year.get(), self.month.get()])
            if name:
                name = f"{name}{sep}{date_part}"
            else:
                name = date_part

        ext = ""
        if self.selected_file:
            ext = Path(self.selected_file).suffix

        self.preview_name.set(f"{name}{ext}")

    # ===== 実行 =====
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
