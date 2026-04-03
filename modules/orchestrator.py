# modules/orchestrator.py

from typing import Dict, Any

from .logger import get_logger
from .bus import bus
from .security import security_manager, SecurityError
from .model_loader import generate_reply  # LLM-ядро
from . import tools  # наши утилиты (калькулятор, конвертер и т.п.)

logger = get_logger("MoriX.orchestrator")


def _extract_last_user_question(raw_text: str) -> str:
    """
    Из всей простыни вроде:

        'Краткая история...\nТы сказал: ...\n...\nНовый вопрос пользователя:\nХХХ'

    выковыриваем только ХХХ (последний реальный вопрос).
    Если маркера нет — возвращаем исходный текст как есть.
    """
    if not raw_text:
        return ""

    marker = "\nНовый вопрос пользователя:\n"
    if marker in raw_text:
        return raw_text.split(marker, 1)[1].strip()

    return raw_text.strip()


def handle_command(input_text: str) -> Dict[str, Any]:
    return _handle(input_text, confirmed=False)


def handle_command_confirmed(input_text: str) -> Dict[str, Any]:
    return _handle(input_text, confirmed=True)


def _handle(input_text: str, *, confirmed: bool) -> Dict[str, Any]:
    scope = "core.echo"

    # ---- 1. Проверка политик безопасности ----
    try:
        security_manager.require(
            scope,
            text=input_text,
            confirmed=confirmed,
            requires_network=False,
            length=len(input_text or ""),
        )
    except SecurityError as e:
        logger.info(f"security_blocked: {e}")
        payload: Dict[str, Any] = {
            "ok": False,
            "type": "security_blocked",
            "error": str(e),
            "scope": scope,
        }
        bus.emit("command.blocked", payload)
        return payload

    # ---- 2. Попытка ответить "инструментами" (калькулятор, конвертер и т.п.) ----
    # Tools должны видеть только последний вопрос, а не всю "краткую историю".
    user_only_text = _extract_last_user_question(input_text or "")

    try:
        tool_reply = tools.try_handle_tools(user_only_text)
    except Exception as ex:
        logger.exception(f"tools.try_handle_tools failed: {ex}")
        tool_reply = None

    if tool_reply is not None:
        reply_text = tool_reply
        payload: Dict[str, Any] = {
            "ok": True,
            "type": "ai_reply",
            "text": reply_text,
            "input": input_text,          # сюда кладём исходный (возможно, с историей)
            "length": len(user_only_text),
            "via": "tool",
        }
        logger.info(
            f"handle_command processed via tool: {user_only_text!r} -> {reply_text!r} (confirmed={confirmed})"
        )
        bus.emit("command.received", payload)
        return payload

    # ---- 3. Если tools не сработали — отправляем в LLM ----
    try:
        reply_text = generate_reply(input_text)
    except Exception as ex:
        logger.exception("LLM error")
        return {
            "ok": False,
            "type": "llm_error",
            "error": str(ex),
            "input": input_text,
        }

    # НИКАКОЙ дополнительной постобработки здесь не делаем:
    # форматирование кода, ``` и т.д. полностью на стороне generate_reply.

    payload: Dict[str, Any] = {
        "ok": True,
        "type": "ai_reply",
        "text": reply_text,
        "input": input_text,
        "length": len(input_text or ""),
    }

    logger.info(
        f"handle_command processed: {input_text!r} -> {reply_text!r} (confirmed={confirmed})"
    )
    bus.emit("command.received", payload)
    return payload
