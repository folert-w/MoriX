#!/usr/bin/env python3
from modules.logger import get_logger
from modules.config import COLORS, FLAGS, DB_PATH, LOGS_DIR  # noqa: F401
from modules.orchestrator import handle_command, handle_command_confirmed
from modules import memory
import json

def main():
    memory.init_db()  # <-- инициализация БД
    logger = get_logger("MoriX.run")
    logger.info("MoriX started")
    print("MoriX console. Type 'exit' to quit.")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text is None:
            continue
        text = text.strip()
        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue

        result = handle_command(text)
        if not result.get("ok") and result.get("error") == "Confirmation required":
            ans = input("Требуется подтверждение. Продолжить? [y/N]: ").strip().lower()
            if ans in {"y", "yes", "д", "да"}:
                result = handle_command_confirmed(text)

        print(json.dumps(result, ensure_ascii=False))
    logger.info("MoriX stopped")

if __name__ == "__main__":
    main()
