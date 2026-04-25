import pygame
from gtts import gTTS
import tempfile
import os
import config


class TextToSpeech:
    def __init__(self):
        pygame.mixer.init()

    def speak(self, text: str):
        print(f"Speaking: {text}")
        tts = gTTS(text=text, lang=config.TTS_LANGUAGE)
        with tempfile.NamedTemporaryFile(suffix=".mp3",
                                         delete=False) as f:
            tts.save(f.name)
            path = f.name
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        os.unlink(path)
