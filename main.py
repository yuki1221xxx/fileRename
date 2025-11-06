import sys
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
    app.geometry("1400x800")

    # 全体ラッパー
    root_frame = tb.Frame(app)
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

    app.mainloop()


if __name__ == "__main__":
    main()
