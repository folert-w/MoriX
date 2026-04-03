from threading import RLock
from pathlib import Path
import tempfile
import subprocess
import shutil



# 🧠 Модель: мультиязычная нейросеть с поддержкой русского
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

_lock = RLock()
_tts = None  # сюда загрузим модель один раз

# Файл для аудио
OUTPUT_FILE = Path(tempfile.gettempdir()) / "morix_tts_coqui.wav"


def _init_tts():
    global _tts
    if _tts is None:
        # ЛЕНИВЫЙ импорт — только когда реально нужен TTS
        from TTS.api import TTS


def say(text: str):
    """
    Оффлайновая озвучка текста с помощью Coqui XTTS v2.
    1) Генерирует wav-файл
    2) Воспроизводит через ffplay без окон
    ВАЖНО: вызывать из отдельного потока (через page.run_thread),
    чтобы не блокировать GUI.
    """
    text = (text or "").strip()
    if not text:
        return

    with _lock:
        _init_tts()

        print(f"[TTS-COQUI] Генерирую речь в {OUTPUT_FILE} ...")
        # XTTS v2 — мультиязычная, явно укажем language="ru"
        # speaker оставляем дефолтный (в модели уже есть встроенные голоса)
        _tts.tts_to_file(
            text=text,
            file_path=str(OUTPUT_FILE),
            language="ru",   # ключевой момент: русская речь
        )

        # 2) Ищем ffplay
        ffplay_path = shutil.which("ffplay")
        if not ffplay_path:
            print("[TTS-COQUI] ffplay не найден в PATH. Установи ffmpeg или добавь ffplay в PATH.")
            print(f"[TTS-COQUI] Аудио лежит тут: {OUTPUT_FILE}")
            return

        print("[TTS-COQUI] Воспроизвожу через ffplay (тихо, без окон)...")
        try:
            subprocess.run(
                [
                    ffplay_path,
                    "-nodisp",          # без окна
                    "-autoexit",        # закрыться после окончания
                    "-loglevel", "quiet",
                    str(OUTPUT_FILE),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as ex:
            print(f"[TTS-COQUI] Ошибка запуска ffplay: {ex}")
