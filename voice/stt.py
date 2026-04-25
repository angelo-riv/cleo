import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import config


class SpeechToText:
    def __init__(self):
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device="cpu",
            compute_type="int8"
        )

    def listen(self, duration: int = 5) -> str:
        print("Listening...")
        audio = sd.rec(
            int(duration * config.MIC_SAMPLE_RATE),
            samplerate=config.MIC_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=config.MIC_DEVICE_INDEX
        )
        sd.wait()
        audio_flat = audio.flatten()
        segments, _ = self.model.transcribe(audio_flat, language="en")
        transcript = " ".join(s.text for s in segments).strip()
        print(f"Heard: {transcript}")
        return transcript
