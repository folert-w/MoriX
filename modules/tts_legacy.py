import subprocess
import edge_tts
import asyncio

async def speak(text):
    communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")  # Теперь русский голос
    await communicate.save("output.mp3")

    # Воспроизводим звук
    import playsound
    subprocess.run(["ffplay", "-nodisp", "-autoexit", "output.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def say(text):
    asyncio.run(speak(text))
