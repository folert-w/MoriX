#!/usr/bin/env python3
import sys, os, traceback, json

# чтобы пакет 'modules' гарантированно подхватился
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from modules.logger import get_logger
# ⚠️ ВАЖНО: не импортируем конкретные имена из config, они здесь не нужны и часто ломают импорт.
# Просто убедимся, что config импортируется (если он кому-то нужен косвенно):
try:
    import modules.config as _cfg  # noqa: F401
except Exception as _e:
    print("WARN: modules.config не импортируется:", _e)

try:
    from modules.orchestrator import handle_command
except Exception as e:
    print("CRASH: не удалось импортировать handle_command из modules.orchestrator:", e)
    traceback.print_exc()
    sys.exit(1)

def main():
    logger = get_logger("MoriX.run")
    logger.info("MoriX CLI started")
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
        try:
            result = handle_command(text)
        except Exception as ex:
            print("Core error:", ex)
            traceback.print_exc()
            continue
        print(json.dumps(result, ensure_ascii=False))
    logger.info("MoriX CLI stopped")

if __name__ == "__main__":
    main()
