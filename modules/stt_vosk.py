import json
import time
from pathlib import Path

import pyaudio
from vosk import Model, KaldiRecognizer


# Путь к модели — под твой реальный путь!
MODEL_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "models"
    / "vosk-model-ru-0.22"
)

_model: Model | None = None
_pa: pyaudio.PyAudio | None = None


def _init_engine():
    """Ленивая инициализация модели Vosk и аудио."""
    global _model, _pa

    if _model is None:
        if not MODEL_DIR.exists():
            raise RuntimeError(
                f"Модель Vosk не найдена по пути: {MODEL_DIR}"
            )
        print(f"[VOSK] Загружаю модель из: {MODEL_DIR}")
        _model = Model(str(MODEL_DIR))

    if _pa is None:
        _pa = pyaudio.PyAudio()


def listen_once(timeout: float = 7.0) -> str:
    """
    Слушает микрофон и возвращает текст (офлайн, через Vosk).
    Важно: вызывать из отдельного потока (через page.run_thread).
    """
    _init_engine()

    rate = 16000
    chunk = 4000

    recognizer = KaldiRecognizer(_model, rate)
    recognizer.SetWords(True)

    stream = _pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=chunk,
    )

    stream.start_stream()

    result_text = ""
    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            data = stream.read(chunk, exception_on_overflow=False)

            if recognizer.AcceptWaveform(data):
                res = json.loads(recognizer.Result())
                txt = (res.get("text") or "").strip()
                if txt:
                    result_text = txt
                    break

        if not result_text:
            res = json.loads(recognizer.FinalResult())
            result_text = (res.get("text") or "").strip()
    finally:
        stream.stop_stream()
        stream.close()

    return result_text
