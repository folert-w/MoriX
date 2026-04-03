from modules.orchestrator import handle_command, handle_command_confirmed
from . import stt_vosk as stt
from . import tts_coqui
import flet as ft
from . import memory
from . import backup


def _apply_window_constraints(p: ft.Page):
    # безопасно выставляем мин. размеры, без ругани Pylance
    for name, value in (("window_min_width", 860), ("window_min_height", 560)):
        if hasattr(p, name):
            setattr(p, name, value)

# Цвета по ТЗ
ORANGE = "#FF6A00"
BLACK = "#000000"
WHITE = "#FFFFFF"
DARK_GRAY = "#2B2B2B"
LIGHT_GRAY = "#F2F2F2"
MID_GRAY = "#D9D9D9"

# Пытаемся использовать твой Core (если он уже подключён как modules/orchestrator с нужными функциями)
try:
    from modules import orchestrator  # ожидаются handle_command, handle_command_confirmed
except Exception:
    import modules.orchestrator as orchestrator

from modules.permission_manager import PermissionManager

class ChatBubble(ft.Container):
    def __init__(self, text: str, side: str = "left", subtle: bool = False):
        is_right = (side == "right")

        # --- Определяем, код это или обычный текст ---
        raw = text or ""
        stripped = raw.strip()

        is_code = False
        code_lang = ""
        code_body = raw

        if stripped.startswith("```"):
            is_code = True
            # убираем первые три бэктика
            tmp = stripped[3:]
            # первая строка — язык (может быть пустой)
            nl = tmp.find("\n")
            if nl == -1:
                code_lang = tmp.strip()
                code_body = ""
            else:
                code_lang = tmp[:nl].strip()
                rest = tmp[nl + 1 :]
                # обрезаем по последним ```
                end = rest.rfind("```")
                if end != -1:
                    code_body = rest[:end]
                else:
                    code_body = rest

        # --- Цвета пузырей: пользователь / MoriX ---
        bg = ORANGE if is_right else LIGHT_GRAY
        color = WHITE if is_right else "#111111"

        if subtle:
            bg = "#1E1E1E" if is_right else "#EFEFEF"
            color = "#CCCCCC" if is_right else "#666666"

        # Для кода сделаем немного другой фон
        if is_code:
            # код всегда рисуем как «ассистентский» пузырь (слева)
            is_right = False
            bg = "#1E1E1E"
            color = "#EEEEEE"

        # --- Контент пузыря ---
        if is_code:
            # заголовок с языком (если есть)
            header = None
            if code_lang:
                header = ft.Text(
                    code_lang,
                    size=12,
                    color="#AAAAAA",
                    italic=True,
                )

            code_text = ft.Text(
                code_body,
                size=13,
                font_family="monospace",
                color=color,
                selectable=True,
                no_wrap=False,  # переносы строк сохраняются
            )

            inner_content_controls = []
            if header:
                inner_content_controls.append(header)
            inner_content_controls.append(code_text)

            inner_content = ft.Column(
                inner_content_controls,
                spacing=4,
                tight=True,
            )
        else:
            inner_content = ft.Text(
                raw,
                size=14,
                color=color,
                selectable=True,
                no_wrap=False,
            )

        super().__init__(
            padding=10,
            margin=ft.margin.only(
                left=8 if is_right else 0,
                right=0 if is_right else 8,
                top=6,
                bottom=6,
            ),
            alignment=ft.alignment.center_right if is_right else ft.alignment.center_left,
            animate=ft.Animation(250, "decelerate"),
            content=ft.Container(
                bgcolor=bg,
                padding=12,
                border_radius=ft.border_radius.only(
                    top_left=16,
                    top_right=16,
                    bottom_left=4 if is_right else 16,
                    bottom_right=16 if is_right else 4,
                ),
                content=inner_content,
            ),
        )


def _truncate_title(title: str, max_len: int = 22) -> str:
    title = (title or "").strip()
    if len(title) <= max_len:
        return title
    return title[: max_len - 1] + "…"


def main(page: ft.Page):
    page.title = "MoriX — GUI"
    page.bgcolor = WHITE
    page.theme_mode = ft.ThemeMode.LIGHT
    _apply_window_constraints(page)

    # флаг текущей темы
    is_dark = True

    def apply_theme():
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.bgcolor = DARK_GRAY if is_dark else WHITE
        page.update()

    def open_drawer(e):
        page.drawer.open = True
        page.update()

    def on_backup_click(e):
        # Покажем результат через всплывающее уведомление
        try:
            path = backup.create_backup()
            msg = f"Бэкап сохранён: {path.name}"
        except Exception as ex:
            msg = f"Ошибка бэкапа: {ex}"

        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()


    # Кнопка-переключатель темы
    theme_button = ft.IconButton(icon="dark_mode")

    def toggle_theme(e):
        nonlocal is_dark
        is_dark = not is_dark
        theme_button.icon = "dark_mode" if is_dark else "light_mode"
        apply_theme()
        load_conversations()  # <-- чтобы цвета текста и фоны перерисовались

    theme_button.on_click = toggle_theme

    # AppBar (верхняя панель)
    page.appbar = ft.AppBar(
        leading=ft.IconButton(icon="menu", on_click=open_drawer),
        title=ft.Text("MoriX — GUI"),
        center_title=False,
        bgcolor=BLACK if is_dark else ORANGE,
        actions=[theme_button],
    )

    # Боковое меню (пока просто заглушка)
    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(
                padding=20,
                content=ft.Text("MoriX V1.2", size=18, weight=ft.FontWeight.BOLD),
            ),
            ft.ListTile(title=ft.Text("Настройки (soon™)")),
            ft.ListTile(title=ft.Text("О ассистенте")),
            ft.ListTile(
                title=ft.Text("Сделать бэкап"),
                on_click=on_backup_click,
            ),
        ]
    )

    apply_theme()  # применяем начальную тему

    pm = PermissionManager(page, primary=ORANGE, text_on_primary=WHITE)

    # Инициализация БД и выбор активного диалога
    memory.init_db()
    current_conv_id = memory.get_default_conversation()

    # Список сообщений
    chat_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)

    # Строка статуса (подсказки, “слушаю…”, ошибки)
    status_text = ft.Text("", color=MID_GRAY, size=12)

    # Поле ввода текста
    input_field = ft.TextField(
        hint_text="Введите сообщение...",
        expand=True,
        border_radius=12,
        border_color=MID_GRAY,
        focused_border_color=ORANGE,
        multiline=False,
        on_submit=lambda e: on_send_click(e),  # при Enter отправляем
    )

    # Хелпер: добавление пузыря сообщения в чат
    def add_message_bubble(text: str, from_user: bool) -> None:
        if not text:
            return

        side = "right" if from_user else "left"
        chat_list.controls.append(ChatBubble(text, side=side))
        page.update()

    def build_llm_input_from_history(history_messages, new_user_text: str) -> str:
        """
        Собираем текст для LLM: короткая история диалога + новый вопрос.
        history_messages — список dict из memory.get_messages(...)
        """
        new_user_text = (new_user_text or "").strip()
        if not history_messages:
            # Если истории нет — отправляем просто текущий текст
            return new_user_text

        lines = []
        # Берём только последние 6 сообщений для контекста
        # get_messages(limit=N) уже отдаёт в хронологическом порядке 
        for msg in history_messages[-6:]:
            role = msg.get("role")
            txt = (msg.get("text") or "").strip()
            if not txt:
                continue

            if role == "user":
                lines.append(f"Ты сказал: {txt}")
            elif role == "assistant":
                lines.append(f"MoriX ответил: {txt}")
            else:
                lines.append(f"Система: {txt}")

        history_block = "\n".join(lines)

        prompt = (
            "Краткая история нашего диалога "
            "Учитывай её смысл, но не повторяй её дословно:\n"
            f"{history_block}\n\n"
            "Новый вопрос пользователя:\n"
            f"{new_user_text}"
        )
        return prompt


    def on_delete_conv(conv_id: int):
        nonlocal current_conv_id

        memory.delete_conversation(conv_id)

        # если удалили активный чат — надо выбрать другой
        if conv_id == current_conv_id:
            convs = memory.list_conversations(limit=1)
            if convs:
                current_conv_id = convs[0]["id"]
                load_chat(current_conv_id)
            else:
                # вообще нет чатов — создаём новый дефолтный
                current_conv_id = memory.create_conversation("Мой первый диалог")
                chat_list.controls.clear()
                page.update()

        load_conversations()  # перерисуем список слева


    def on_clear_conv(conv_id: int):
        nonlocal current_conv_id

        memory.clear_messages(conv_id)
        if conv_id == current_conv_id:
            # очищаем историю на экране, но чат оставляем
            chat_list.controls.clear()
            page.update()
        load_conversations()

        def on_backup_click(e):
          nonlocal status_text
          try:
            path = backup.create_backup()
            status_text.value = f"Бэкап сохранён: {path.name}"
          except Exception as ex:
            status_text.value = f"Ошибка бэкапа: {ex}"
          page.update()



    def on_rename_conv(conv_id: int):
        nonlocal current_conv_id

        # простейший вариант — через input_dialog
        def on_ok(e):
            new_title = title_field.value.strip() or "Без названия"
            memory.rename_conversation(conv_id, new_title)
            load_conversations()
            page.close(dialog)

        title_field = ft.TextField(label="Новое название чата", width=300)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Переименовать чат"),
            content=title_field,
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("OK", on_click=on_ok),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        page.open(dialog)


    # Универсальная отправка сообщения (и с текста, и с голоса)
        # Универсальная отправка сообщения (и с текста, и с голоса)
    def _send_message_from_text(text: str):
        nonlocal status_text

        text = (text or "").strip()
        if not text:
            return

        # 1) Пузырь от пользователя на экране (что именно он ввёл)
        add_message_bubble(text, from_user=True)
        page.update()

        # 2) Берём историю из БД ДО сохранения текущего сообщения
        #    чтобы в контексте были только предыдущие реплики
        history_msgs = memory.get_messages(current_conv_id, limit=20)

        # 3) Строим вход для LLM: история + новый вопрос
        llm_input = build_llm_input_from_history(history_msgs, text)

        # 4) Обработка через оркестратор
        try:
            resp = handle_command(llm_input)
        except Exception as ex:
            add_message_bubble(f"[Ошибка обработки: {ex}]", from_user=False)
            page.update()
            return

        if not resp.get("ok"):
            # Например, блокировка безопасностью
            err = resp.get("error", "Unknown error")
            add_message_bubble(f"[Заблокировано безопасностью: {err}]", from_user=False)
            page.update()
            return

        # 5) Пузырь от MoriX
        bot_text = resp.get("text") or resp.get("input") or ""
        add_message_bubble(bot_text, from_user=False)
        page.update()

        # 6) Сохраняем в БД и вопрос пользователя, и ответ ассистента
        memory.add_message(current_conv_id, "user", text)
        memory.add_message(current_conv_id, "assistant", bot_text)

        # 7) Озвучка ответа MoriX в отдельном потоке
        def speak_worker():
            nonlocal status_text
            try:
                tts_coqui.say(bot_text)
            except Exception as ex:
                status_text.value = f"Ошибка озвучки: {ex}"
                page.update()

        page.run_thread(speak_worker)


    def load_history():
        chat_list.controls.clear()
        msgs = memory.get_messages(current_conv_id, limit=100)  # последние 100
        for msg in msgs:
            from_user = (msg["role"] == "user")
            add_message_bubble(msg["text"], from_user=from_user)
        page.update()

    def load_conversations():
        # оставляем только первые 4 элемента (шапка + 3 статичных пункта)
        page.drawer.controls = page.drawer.controls[:4]

        # Кнопка "Новый чат"
        page.drawer.controls.append(
            ft.IconButton(
                icon="add",
                on_click=on_create_new_chat,
            )
        )

        conversations = memory.list_conversations(limit=50)

        for conv in conversations:
            conv_id = conv["id"]
            is_active = (conv_id == current_conv_id)

            # Цвета для активного / неактивного чата
            if is_active:
                if is_dark:
                    tile_bg = "#333333"     # чуть светлее общего фона drawer
                    title_color = WHITE
                else:
                    tile_bg = "#FFE2CC"     # мягкий светло-оранжевый
                    title_color = BLACK
            else:
                if is_dark:
                    tile_bg = "#1E1E1E"     # тёмно-серый фон карточки
                    title_color = WHITE
                else:
                    tile_bg = "#F5F5F5"     # светло-серый фон
                    title_color = BLACK

            page.drawer.controls.append(
                ft.Container(
                    bgcolor=tile_bg,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    margin=ft.margin.symmetric(horizontal=6, vertical=4),
                    border=ft.border.all(1, "#00000020" if is_dark else "#DDDDDD"),
                    content=ft.ListTile(
                        title=ft.Text(
                            _truncate_title(conv["title"]),
                             color=title_color,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            size=14,
                        ),
                        on_click=lambda e, cid=conv_id: load_chat(cid),
                        trailing=ft.PopupMenuButton(
                            items=[
                                ft.PopupMenuItem(
                                    text="Переименовать",
                                    on_click=lambda e, cid=conv_id: on_rename_conv(cid),
                                ),
                                ft.PopupMenuItem(
                                    text="Очистить историю",
                                    on_click=lambda e, cid=conv_id: on_clear_conv(cid),
                                ),
                                ft.PopupMenuItem(
                                    text="Удалить чат",
                                    on_click=lambda e, cid=conv_id: on_delete_conv(cid),
                                ),
                             ]
                         ),
                    ),
                )
            )

        page.update()




    def on_create_new_chat(e):
      nonlocal current_conv_id

      title = "Новый чат"
      new_conv_id = memory.create_conversation(title)

      current_conv_id = new_conv_id   # сразу делаем его активным
      load_conversations()            # перерисовали список чатов
      load_chat(new_conv_id)          # открыли новый диалог


    def load_chat(conv_id: int):
      nonlocal current_conv_id
      current_conv_id = conv_id  # теперь этот чат считается активным

      messages = memory.get_messages(conv_id)
      chat_list.controls.clear()

      for msg in messages:
          add_message_bubble(msg["text"], from_user=(msg["role"] == "user"))

      page.update()
      # ВАЖНО: перерисовать список чатов с учётом нового current_conv_id
      load_conversations()


    # Отправка по кнопке "Send"
    def on_send_click(e):
        _send_message_from_text(input_field.value)
        input_field.value = ""
        page.update()

    # Голосовая кнопка 🎤
    def on_mic_click(e: ft.ControlEvent):
        # Покажем, что слушаем
        status_text.value = "🎙 MoriX слушает..."
        page.update()

        def worker():
            nonlocal status_text

            try:
                text = stt.listen_once()
            except Exception as ex:
                status_text.value = f"Ошибка голосового ввода: {ex}"
                page.update()
                return

            if not text:
                status_text.value = "Не разобрал, попробуй ещё раз."
                page.update()
                return

            # Покажем распознанное
            status_text.value = ""
            page.update()

            # Отправим его так же, как если бы ты нажал Enter
            _send_message_from_text(text)

        # Запуск в отдельном потоке, чтобы не вешать UI
        page.run_thread(worker)

    # Кнопки
    send_button = ft.IconButton(icon="send", on_click=on_send_click)
    mic_button = ft.IconButton(
        icon="mic",
        tooltip="Голосовой ввод",
        on_click=on_mic_click,
    )

    # Нижняя панель (ввод + кнопки)
    bottom_row = ft.Row(
        controls=[
            input_field,
            mic_button,
            send_button,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    load_conversations()  # Загружаем чаты в боковом меню
    load_history()  # Загружаем историю сообщений для текущего чата
    

    # Компоновка на странице
    page.add(
        chat_list,
        status_text,
        bottom_row,
    )

