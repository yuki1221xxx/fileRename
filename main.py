import sys
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import ttkbootstrap as tb

from file_row_widget import FileRowWidget
from utils import (
    ensure_initial_config,
    get_row_indices,
    add_row_config,
    delete_row_config,
    normalize_row_configs,
)


def main():
    # 初回分がなければ5行つくる
    ensure_initial_config(default_rows=5)
    # 起動時点で欠番があっても詰めておく
    normalize_row_configs()

    app = tb.Window(themename="cosmo")
    app.title("ファイル一括リネーム＆移動")

    screen_w = app.winfo_screenwidth()
    screen_h = app.winfo_screenheight()
    width = min(max(1024, int(screen_w * 0.96)), screen_w - 10)
    height = min(max(720, int(screen_h * 0.94)), screen_h - 30)
    app.geometry(f"{width}x{height}+10+10")
    try:
        app.state("zoomed")  # Windowsなら最大化して大きく見せる
    except Exception:
        pass
    app.minsize(820, 560)

    style = app.style
    base_font = ("Meiryo UI", 12)
    small_font = ("Meiryo UI", 11)
    app.tk.call("tk", "scaling", 1.2)
    app.option_add("*Font", base_font)
    app.option_add("*Listbox.font", base_font)
    app.option_add("*TEntry.Font", base_font)
    app.option_add("*TCombobox*Listbox.font", base_font)
    style.configure(".", font=base_font)
    style.configure("TNotebook.Tab", font=("Meiryo UI", 12, "bold"), padding=(14, 8))
    style.configure("TButton", font=base_font, padding=8)
    style.configure("TLabel", font=base_font)
    style.configure("TEntry", font=base_font, padding=8)
    style.configure("TCombobox", font=base_font)
    style.configure("TCheckbutton", font=small_font)

    # ノートブック（タブ）を用意
    notebook = tb.Notebook(app)
    notebook.pack(fill="both", expand=True)

    # === リネームタブ ===
    rename_tab = tb.Frame(notebook)
    notebook.add(rename_tab, text="リネーム")

    # 全体ラッパー
    root_frame = tb.Frame(rename_tab)
    root_frame.pack(fill="both", expand=True)

    # ───────── 上：ヘッダー（固定）─────────
    header = tb.Frame(root_frame)
    header.pack(side="top", fill="x", padx=5, pady=5)

    # ───────── 下：スクロール領域（Canvas方式）─────────
    scroll_frame = tb.Frame(root_frame)
    scroll_frame.pack(side="top", fill="both", expand=True)

    canvas = tb.Canvas(scroll_frame, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    v_scroll = tb.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
    v_scroll.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=v_scroll.set)

    # キャンバスの中に実際の行を並べるフレームを1つ置く
    rows_container = tb.Frame(canvas)
    container_id = canvas.create_window((0, 0), window=rows_container, anchor="nw")

    def on_canvas_configure(event):
        # 横幅はキャンバスに合わせる
        canvas.itemconfig(container_id, width=event.width)
        # 必ず(0,0)に固定
        try:
            canvas.moveto(container_id, 0, 0)
        except Exception:
            canvas.coords(container_id, 0, 0)

    canvas.bind("<Configure>", on_canvas_configure)

    widgets = {}

    # 一番上を表示する共通関数
    def reset_scroll_to_top():
        app.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        try:
            canvas.moveto(container_id, 0, 0)
        except Exception:
            canvas.coords(container_id, 0, 0)
        canvas.yview_moveto(0.0)

    # ───────── 行を全部作り直す関数 ─────────
    def build_rows():
        for w in widgets.values():
            w.destroy()
        widgets.clear()

        indices = get_row_indices()
        for idx in indices:
            w = FileRowWidget(rows_container, idx, on_delete=handle_delete)
            widgets[idx] = w
            w.card.grid(row=idx, column=0, sticky="nsew", padx=5, pady=5)

        rows_container.columnconfigure(0, weight=1)
        reset_scroll_to_top()
        app.after(60, reset_scroll_to_top)

    # ───────── 削除時の処理 ─────────
    def handle_delete(idx: int):
        delete_row_config(idx)
        normalize_row_configs()
        build_rows()

    # ───────── 行追加ボタン ─────────
    def add_new_row():
        normalize_row_configs()
        indices = get_row_indices()
        next_index = len(indices)
        add_row_config(next_index)
        build_rows()

    add_btn = tb.Button(header, text="＋ 行を追加", bootstyle="primary", command=add_new_row)
    add_btn.pack(side="left")

    # ───────── マウスホイールでスクロールできるようにする ─────────
    def _on_mousewheel(event):
        # Windows / 一部Linux
        delta = event.delta
        if sys.platform.startswith("win"):
            # 120 が1ノッチ
            canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        else:
            # 他環境でもとりあえずdeltaを見る
            canvas.yview_scroll(int(-1 * (delta)), "units")

    def _on_mousewheel_linux(event):
        # LinuxでButton-4/5を使う場合
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")

    # どのウィジェットにフォーカスがあってもスクロールできるように全体にバインド
    app.bind_all("<MouseWheel>", _on_mousewheel)
    app.bind_all("<Button-4>", _on_mousewheel_linux)
    app.bind_all("<Button-5>", _on_mousewheel_linux)

    # 初期の行を表示
    build_rows()

    # === ZIP化タブ ===
    zip_tab = tb.Frame(notebook)
    notebook.add(zip_tab, text="ZIP化")

    zip_frame = tb.Labelframe(zip_tab, text="フォルダをZIP化", bootstyle="secondary")
    zip_frame.pack(fill="x", padx=10, pady=10)
    zip_frame.columnconfigure(1, weight=1)

    zip_source = tk.StringVar()
    zip_dest = tk.StringVar()
    zip_name = tk.StringVar()
    zip_status = tk.StringVar()

    def choose_zip_source():
        folder = filedialog.askdirectory()
        if folder:
            zip_source.set(folder)
            # 初期値として親フォルダとフォルダ名を提案
            if not zip_dest.get():
                zip_dest.set(str(Path(folder).parent))
            if not zip_name.get():
                zip_name.set(Path(folder).name)

    def choose_zip_dest():
        folder = filedialog.askdirectory()
        if folder:
            zip_dest.set(folder)

    def set_status(message, style="info"):
        zip_status.set(message)
        color = {"info": "info", "success": "success", "danger": "danger"}.get(style, "info")
        status_label.configure(bootstyle=color)

    def perform_zip():
        src = zip_source.get()
        dest_dir = zip_dest.get()
        name = zip_name.get().strip()

        if not src or not os.path.isdir(src):
            set_status("⚠ フォルダが選択されていません", "danger")
            return
        if not dest_dir:
            set_status("⚠ 保存先フォルダを指定してください", "danger")
            return
        if not name:
            set_status("⚠ ZIP名を入力してください", "danger")
            return

        zip_dest_path = Path(dest_dir)
        if not zip_dest_path.exists():
            try:
                zip_dest_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("エラー", f"保存先フォルダを作成できませんでした:\n{e}")
                return

        # 拡張子を整理
        zip_stem = name[:-4] if name.lower().endswith(".zip") else name
        archive_base = zip_dest_path / zip_stem

        try:
            out_path = shutil.make_archive(str(archive_base), "zip", root_dir=src)
            set_status(f"✅ 作成完了: {Path(out_path).name}", "success")
        except Exception as e:
            messagebox.showerror("エラー", f"ZIP作成中に問題が発生しました:\n{e}")
            set_status("⚠ 失敗しました", "danger")

    tb.Label(zip_frame, text="対象フォルダ").grid(row=0, column=0, sticky="w", padx=5, pady=3)
    btn_src = tb.Button(zip_frame, text="フォルダ選択", bootstyle="primary", command=choose_zip_source)
    btn_src.grid(row=0, column=2, sticky="e", padx=5, pady=3)
    tb.Entry(zip_frame, textvariable=zip_source, state="readonly").grid(row=0, column=1, sticky="ew", padx=5, pady=3)

    tb.Label(zip_frame, text="保存先フォルダ").grid(row=1, column=0, sticky="w", padx=5, pady=3)
    btn_dest = tb.Button(zip_frame, text="保存先選択", bootstyle="secondary", command=choose_zip_dest)
    btn_dest.grid(row=1, column=2, sticky="e", padx=5, pady=3)
    tb.Entry(zip_frame, textvariable=zip_dest, state="readonly").grid(row=1, column=1, sticky="ew", padx=5, pady=3)

    tb.Label(zip_frame, text="ZIPファイル名").grid(row=2, column=0, sticky="w", padx=5, pady=3)
    tb.Entry(zip_frame, textvariable=zip_name).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
    tb.Label(zip_frame, text=".zip は自動で付きます").grid(row=2, column=2, sticky="e", padx=5, pady=3)

    action_row = tb.Frame(zip_frame)
    action_row.grid(row=3, column=0, columnspan=3, sticky="w", padx=5, pady=8)
    tb.Button(action_row, text="ZIP化する", bootstyle="success", command=perform_zip).pack(side="left")
    status_label = tb.Label(action_row, textvariable=zip_status, bootstyle="info")
    status_label.pack(side="left", padx=10)

    app.mainloop()


if __name__ == "__main__":
    main()
