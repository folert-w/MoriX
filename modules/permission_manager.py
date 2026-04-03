from __future__ import annotations
from typing import Callable, Optional
import flet as ft

class PermissionManager:
    def __init__(self, page: ft.Page, primary: str = "#FF6A00", text_on_primary: str = "#FFFFFF"):
        self.page = page
        self.primary = primary
        self.text_on_primary = text_on_primary
        self._dlg: Optional[ft.AlertDialog] = None

    def confirm(self, title: str, message: str, on_result: Callable[[bool], None],
                yes_label: str = "Да", no_label: str = "Нет") -> None:
        def _yes(_):
            self._close()
            on_result(True)

        def _no(_):
            self._close()
            on_result(False)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.W_600),
            content=ft.Text(message),
            actions=[
                ft.TextButton(no_label, on_click=_no),
                ft.FilledButton(
                    yes_label,
                    on_click=_yes,
                    style=ft.ButtonStyle(bgcolor=self.primary, color=self.text_on_primary),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._dlg = dlg
        # вместо page.dialog = dlg; dlg.open = True
        self.page.open(dlg)

    def _close(self):
        if self._dlg:
            try:
                self.page.close(self._dlg)
            finally:
                self._dlg = None
