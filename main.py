# main.py
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from file_row_widget import FileRowWidget

def main():
    # ttkbootstrapのウィンドウ
    app = tb.Window(themename="cosmo")
    app.title("ファイル一括リネーム＆移動")

    # 画面全体を1つのフレームで受ける
    container = tb.Frame(app, padding=5)
    container.grid(row=0, column=0, sticky="nsew")

    # ウィンドウが広がったら中も広がるように
    app.rowconfigure(0, weight=1)
    app.columnconfigure(0, weight=1)

    # 5行分を作成
    for i in range(5):
        FileRowWidget(container, i)
        container.rowconfigure(i, weight=1)

    # 1列なので1列を広がるように
    container.columnconfigure(0, weight=1)

    app.geometry("1400x800")  # 初期サイズは大きめにしておく
    app.mainloop()

if __name__ == "__main__":
    main()
