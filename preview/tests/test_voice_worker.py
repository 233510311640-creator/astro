import io
import json
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
    def test_length_framing_and_reusable_model(self):
        self.assertEqual(voice_worker.read_exact(io.BytesIO(b"abcd"), 4), b"abcd")
        self.assertIsNone(voice_worker.read_exact(io.BytesIO(b"a"), 4))

    def test_serve_loads_model_once_for_two_requests(self):
        sample = pcm_wav()
        stream = io.BytesIO(struct.pack("<I", len(sample)) + sample + struct.pack("<I", len(sample)) + sample)
        output = io.StringIO()
        cached = object()
        with patch.object(voice_worker, "load_model", return_value=cached) as load, \
             patch.object(voice_worker, "transcribe", return_value={"status": "ok", "text": "hello"}) as transcribe, \
             patch.object(voice_worker.sys, "stdin", types.SimpleNamespace(buffer=stream)), \
             patch.object(voice_worker.sys, "stdout", output):
            self.assertEqual(voice_worker.serve(Path("unused")), 0)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(transcribe.call_count, 2)
        self.assertIs(transcribe.call_args.args[2], cached)
        self.assertEqual(output.getvalue().splitlines()[0], "READY")
        self.assertEqual(json.loads(output.getvalue().splitlines()[2])["text"], "hello")

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
