import flet as ft
from modules.gui import main as gui_main
from modules import memory 


if __name__ == "__main__":
    memory.init_db()
    print("OK: modules.gui импортирован, запускаю Flet app...")
    ft.app(
        target=gui_main,                 # <--- сразу передаём gui.main
        view=ft.AppView.WEB_BROWSER,     # открывается в браузере
        port=8550,
        host="0.0.0.0",                  # <--- даёт доступ с других устройств в сети
    )
