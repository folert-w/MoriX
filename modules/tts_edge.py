import asyncio
from threading import RLock
from pathlib import Path
import tempfile
import subprocess
import shutil

import edge_tts

VOICE = "ru-RU-DmitryNeural"

# Файл в безопасной временной папке (без кириллицы и пробелов)
OUTPUT_FILE = Path(tempfile.gettempdir()) / "morix_tts_output.mp3"

_lock = RLock()


async def _speak_async(text: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(OUTPUT_FILE))


def say(text: str):
    """
    Озвучивает текст через Microsoft Edge TTS (онлайн) и воспроизводит через ffplay.
    Без сторонних окон, только звук.
    ВАЖНО: вызывать из отдельного потока (через page.run_thread).
    """
    text = (text or "").strip()
    if not text:
        return

    with _lock:
        # 1) Генерируем mp3 через edge-tts
        asyncio.run(_speak_async(text))

        # 2) Ищем ffplay
        ffplay_path = shutil.which("ffplay")
        if not ffplay_path:
            print("[TTS] ffplay не найден в PATH. Установи ffmpeg или добавь ffplay в PATH.")
            print(f"[TTS] Файл с озвучкой лежит тут: {OUTPUT_FILE}")
            return

        # 3) Тихо воспроизводим через ffplay
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
            print(f"[TTS] Ошибка запуска ffplay: {ex}")
