import sys
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from file_row_widget import FileRowWidget
from utils import (
    ensure_initial_config,
    get_row_indices,
    add_row_config,
    delete_row_config,
    normalize_row_configs,
)

APP_BG = "#eef0f3"
CARD_BG = "#ffffff"


def _btn(parent, text, cmd, bg="#6c757d", font_bold=False, px=10, py=5):
    f = ("Meiryo UI", 10, "bold") if font_bold else ("Meiryo UI", 10)
    r = max(0, int(bg[1:3], 16) - 30)
    g = max(0, int(bg[3:5], 16) - 30)
    b = max(0, int(bg[5:7], 16) - 30)
    dark = f"#{r:02x}{g:02x}{b:02x}"
    return tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg="white", activebackground=dark, activeforeground="white",
        font=f, relief="flat", cursor="hand2", padx=px, pady=py,
    )


def _setup_styles(app):
    s = ttk.Style(app)
    s.theme_use("clam")
    F = ("Meiryo UI", 10)
    FB = ("Meiryo UI", 10, "bold")
    s.configure(".", font=F, background=APP_BG)
    s.configure("TFrame", background=APP_BG)
    s.configure("TLabel", background=APP_BG, font=F)
    s.configure("TScrollbar", troughcolor="#dee2e6", background="#adb5bd", arrowcolor="#6c757d")
    s.configure("TNotebook", background=APP_BG, tabmargins=[2, 0, 0, 0])
    s.configure("TNotebook.Tab", font=FB, padding=(18, 7))
    s.map("TNotebook.Tab",
          background=[("selected", CARD_BG), ("!selected", "#d3d7db")],
          foreground=[("selected", "#212529"), ("!selected", "#495057")])
    s.configure("TEntry", fieldbackground=CARD_BG, padding=5)
    s.configure("TCombobox", fieldbackground=CARD_BG, padding=5)
    s.map("TCombobox", fieldbackground=[("readonly", CARD_BG), ("disabled", "#e9ecef")])
    s.map("TEntry", fieldbackground=[("disabled", "#e9ecef"), ("readonly", "#e9ecef")])


def main():
    ensure_initial_config(default_rows=3)
    normalize_row_configs()

    app = tk.Tk()
    app.title("ファイル リネーム & 移動")
    app.configure(bg=APP_BG)

    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    w = min(1020, sw - 60)
    h = min(760, sh - 80)
    app.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    app.minsize(720, 520)

    _setup_styles(app)

    nb = ttk.Notebook(app)
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    # ─── リネームタブ ───────────────────────────────────────────
    rename_tab = tk.Frame(nb, bg=APP_BG)
    nb.add(rename_tab, text="  リネーム  ")

    header = tk.Frame(rename_tab, bg=APP_BG)
    header.pack(fill="x", padx=8, pady=(6, 4))

    widgets = {}

    def build_rows():
        for w_obj in widgets.values():
            w_obj.destroy()
        widgets.clear()
        for idx in get_row_indices():
            w_obj = FileRowWidget(rows_container, idx, on_delete=handle_delete)
            widgets[idx] = w_obj
            w_obj.frame.pack(fill="x", padx=6, pady=6)
        rows_container.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.yview_moveto(0.0)

    def handle_delete(idx):
        delete_row_config(idx)
        normalize_row_configs()
        build_rows()

    def add_new_row():
        normalize_row_configs()
        add_row_config(len(get_row_indices()))
        build_rows()

    _btn(header, "＋ 行を追加", add_new_row, bg="#0d6efd", font_bold=True).pack(side="left")

    scroll_area = tk.Frame(rename_tab, bg=APP_BG)
    scroll_area.pack(fill="both", expand=True)

    canvas = tk.Canvas(scroll_area, bg=APP_BG, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    vsb = ttk.Scrollbar(scroll_area, orient="vertical", command=canvas.yview)
    vsb.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=vsb.set)

    rows_container = tk.Frame(canvas, bg=APP_BG)
    cid = canvas.create_window((0, 0), window=rows_container, anchor="nw")

    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cid, width=e.width))
    rows_container.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )

    def _close_combobox_popup():
        # スクロール前に開いているComboboxのドロップダウンを閉じる
        try:
            app.tk.eval("catch {ttk::combobox::Unpost}")
        except Exception:
            pass

    def _on_wheel(event):
        _close_combobox_popup()
        canvas.yview_scroll(int(-event.delta / 120), "units")

    def _safe_yview(*args):
        _close_combobox_popup()
        canvas.yview(*args)

    vsb.configure(command=_safe_yview)
    app.bind_all("<MouseWheel>", _on_wheel)

    build_rows()

    # ─── ZIPタブ ────────────────────────────────────────────────
    zip_tab = tk.Frame(nb, bg=APP_BG)
    nb.add(zip_tab, text="  ZIP化  ")

    border_outer = tk.Frame(zip_tab, bg="#c8cdd4")
    border_outer.pack(fill="x", padx=20, pady=20)
    card = tk.Frame(border_outer, bg=CARD_BG)
    card.pack(fill="both", expand=True, padx=1, pady=1)

    ch = tk.Frame(card, bg="#495057")
    ch.pack(fill="x")
    tk.Label(ch, text="  フォルダをZIP化", bg="#495057", fg="white",
             font=("Meiryo UI", 11, "bold"), anchor="w", pady=8).pack(fill="x")

    body = tk.Frame(card, bg=CARD_BG)
    body.pack(fill="x", padx=16, pady=14)
    body.columnconfigure(1, weight=1)

    zip_source = tk.StringVar()
    zip_dest = tk.StringVar()
    zip_name = tk.StringVar()
    zip_status_var = tk.StringVar()

    def choose_zip_source():
        folder = filedialog.askdirectory()
        if folder:
            zip_source.set(folder)
            if not zip_dest.get():
                zip_dest.set(str(Path(folder).parent))
            if not zip_name.get():
                zip_name.set(Path(folder).name)

    def choose_zip_dest():
        folder = filedialog.askdirectory()
        if folder:
            zip_dest.set(folder)

    def perform_zip():
        src = zip_source.get()
        dest_dir = zip_dest.get()
        name = zip_name.get().strip()
        if not src or not os.path.isdir(src):
            zip_status_var.set("⚠ フォルダが選択されていません")
            status_lbl.configure(fg="#dc3545")
            return
        if not dest_dir:
            zip_status_var.set("⚠ 保存先フォルダを指定してください")
            status_lbl.configure(fg="#dc3545")
            return
        if not name:
            zip_status_var.set("⚠ ZIP名を入力してください")
            status_lbl.configure(fg="#dc3545")
            return
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        stem = name[:-4] if name.lower().endswith(".zip") else name
        try:
            out = shutil.make_archive(str(Path(dest_dir) / stem), "zip", root_dir=src)
            zip_status_var.set(f"✅ 完了: {Path(out).name}")
            status_lbl.configure(fg="#198754")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            zip_status_var.set("⚠ 失敗しました")
            status_lbl.configure(fg="#dc3545")

    def zip_row(row, label, var, btn_text, btn_cmd, btn_color="#6c757d"):
        tk.Label(body, text=label, bg=CARD_BG, font=("Meiryo UI", 10), anchor="w")\
            .grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
        ttk.Entry(body, textvariable=var, state="readonly")\
            .grid(row=row, column=1, sticky="ew", pady=5)
        _btn(body, btn_text, btn_cmd, bg=btn_color, px=10, py=4)\
            .grid(row=row, column=2, sticky="e", pady=5, padx=(8, 0))

    zip_row(0, "対象フォルダ", zip_source, "選択", choose_zip_source, "#0d6efd")
    zip_row(1, "保存先フォルダ", zip_dest, "選択", choose_zip_dest, "#6c757d")

    tk.Label(body, text="ZIPファイル名", bg=CARD_BG, font=("Meiryo UI", 10), anchor="w")\
        .grid(row=2, column=0, sticky="w", pady=5, padx=(0, 12))
    ttk.Entry(body, textvariable=zip_name)\
        .grid(row=2, column=1, sticky="ew", pady=5)
    tk.Label(body, text="(.zip 自動付加)", bg=CARD_BG, font=("Meiryo UI", 9), fg="#6c757d")\
        .grid(row=2, column=2, sticky="e", padx=(8, 0), pady=5)

    ar = tk.Frame(body, bg=CARD_BG)
    ar.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 4))
    _btn(ar, "  ZIP化する  ", perform_zip, bg="#198754", font_bold=True, py=6).pack(side="left")
    status_lbl = tk.Label(ar, textvariable=zip_status_var, bg=CARD_BG,
                          font=("Meiryo UI", 10), fg="#198754")
    status_lbl.pack(side="left", padx=12)

    app.mainloop()


if __name__ == "__main__":
    main()
