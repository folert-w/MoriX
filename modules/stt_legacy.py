import speech_recognition as sr

# Один общий распознаватель на модуль
_recognizer = sr.Recognizer()


def listen_once(
    timeout: float = 5.0,
    phrase_time_limit: float = 10.0,
    language: str = "ru-RU",
) -> str:
    """
    Слушает микрофон один раз и возвращает распознанный текст.
    Если ничего не понято – возвращает пустую строку.
    Если проблемы с сетью/сервисом – кидает RuntimeError.
    """
    with sr.Microphone() as source:
        # Немного подстроиться под фон
        _recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("🎙 Слушаю… Говори.")
        audio = _recognizer.listen(
            source,
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
        )

    try:
        text = _recognizer.recognize_google(audio, language=language)
        print(f"🗣 Распознал: {text}")
        return text
    except sr.UnknownValueError:
        # Не смог распознать
        print("🤔 Не разобрал, что ты сказал.")
        return ""
    except sr.RequestError as e:
        # Проблема с сервисом Google
        raise RuntimeError(f"Ошибка сервиса распознавания речи: {e}")
