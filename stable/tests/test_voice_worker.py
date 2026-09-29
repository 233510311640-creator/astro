import io
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave

from local_assistant import voice_worker


def pcm_wav(amplitude=9000, rate=16000, seconds=1):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(rate)
        recording.writeframes(struct.pack(f"<{rate * seconds}h", *([amplitude] * (rate * seconds))))
    return stream.getvalue()


class VoiceWorkerTests(unittest.TestCase):
    def test_accepts_bounded_mono_pcm_and_rejects_invalid_audio(self):
        self.assertEqual(len(voice_worker.read_pcm_wav(pcm_wav())), 16000)
        self.assertTrue(voice_worker.self_test())
        for invalid in (b"", b"not a wave", pcm_wav(seconds=21)):
            with self.subTest(size=len(invalid)), self.assertRaises(voice_worker.VoiceInputError):
                voice_worker.read_pcm_wav(invalid)

    def test_uses_only_explicit_local_model_and_bounded_draft(self):
        calls = []

        class FakeModel:
            def __init__(self, path, **options):
                calls.append((path, options))

            def transcribe(self, samples, **options):
                self_test.assertEqual(len(samples), 16000)
                self_test.assertEqual(options["language"], "en")
                self_test.assertFalse(options["condition_on_previous_text"])
                return iter((types.SimpleNamespace(text="  open   notes  "),)), None

        self_test = self
        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeModel
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "model.bin").write_bytes(b"test fixture")
            (model / "tokenizer.json").write_text("{}", encoding="utf-8")
            with patch.dict(sys.modules, {"faster_whisper": fake_module}):
                result = voice_worker.transcribe(pcm_wav(), model)
        self.assertEqual(result, {"status": "ok", "text": "open notes"})
        self.assertEqual(calls[0][1]["local_files_only"], True)
        self.assertEqual(calls[0][1]["device"], "cpu")

    def test_silence_never_loads_model(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "model.bin").write_bytes(b"test fixture")
            (model / "tokenizer.json").write_text("{}", encoding="utf-8")
            result = voice_worker.transcribe(pcm_wav(amplitude=0), model)
        self.assertEqual(result, {"status": "no_speech", "text": ""})


if __name__ == "__main__":
    unittest.main()
