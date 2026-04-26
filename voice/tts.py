import pygame
from gtts import gTTS
import tempfile
import os
import config
from utils.logger import log


class TextToSpeech:
    def __init__(self):
        pygame.mixer.init()
        self._elevenlabs = None
        if config.ELEVENLABS_API_KEY:
            try:
                from elevenlabs.client import ElevenLabs
                self._elevenlabs = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
                log("ElevenLabs TTS initialized", level="info")
            except ImportError:
                log("elevenlabs package not installed — falling back to gTTS", level="warn")
            except Exception as e:
                log(f"ElevenLabs init failed ({e}) — falling back to gTTS", level="warn")

    def speak(self, text: str):
        print(f"Speaking: {text}")
        if self._elevenlabs and self._speak_elevenlabs(text):
            return
        self._speak_gtts(text)

    def _speak_elevenlabs(self, text: str) -> bool:
        try:
            audio = self._elevenlabs.text_to_speech.convert(
                voice_id=config.ELEVENLABS_VOICE_ID,
                text=text,
                model_id=config.ELEVENLABS_MODEL,
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                for chunk in audio:
                    f.write(chunk)
                path = f.name
            self._play_and_delete(path)
            return True
        except Exception as e:
            log(f"ElevenLabs TTS failed ({e}), falling back to gTTS", level="warn")
            return False

    def _speak_gtts(self, text: str):
        tts = gTTS(text=text, lang=config.TTS_LANGUAGE)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts.save(f.name)
            path = f.name
        self._play_and_delete(path)

    def _play_and_delete(self, path: str):
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        os.unlink(path)
