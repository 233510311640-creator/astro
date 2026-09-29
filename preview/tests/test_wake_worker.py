import pathlib
import base64
from collections import deque
import io
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave
import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from local_assistant import wake_worker


class WakeWorkerTests(unittest.TestCase):
    def test_explicit_phrases_and_spoken_stop(self):
        self.assertIn("HELLO CYPHER", wake_worker.PHRASES)
        self.assertIn("CYPHER", wake_worker.PHRASES)
        self.assertIn("CYPHER STOP", wake_worker.PHRASES)
        self.assertEqual(len(wake_worker.PHRASES), len(set(wake_worker.PHRASES)))

    def test_worker_protocol_exposes_no_ambient_transcript(self):
        source = pathlib.Path(wake_worker.__file__).read_text(encoding="utf-8")
        self.assertIn('print("READY", flush=True)', source)
        self.assertIn('print("SIGNAL", flush=True)', source)
        self.assertIn('print("WAKE", flush=True)', source)
        self.assertIn('base64.b64encode(make_wave(chunks))', source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.", source)
        self.assertNotIn("str(exc)", source)

    def test_tuning_is_bounded_and_stop_is_not_boosted(self):
        tokens = [["a"] for _ in wake_worker.PHRASES]
        lines = list(wake_worker.phrase_lines(tokens, 1.5, 0.35))
        self.assertIn(":1.50 #0.35 @HELLO_CYPHER", lines[0])
        self.assertIn(":1.00 #0.25 @CYPHER_STOP", lines[-2])
        with self.assertRaises(wake_worker.WakeWorkerError):
            list(wake_worker.phrase_lines(tokens, 4.0, 0.1))

    def test_phonetic_model_uses_english_lexicon(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = pathlib.Path(temporary)
            for name in ("tokens.txt", "en.phone", "encoder-1.onnx", "decoder-1.onnx", "joiner-1.onnx"):
                (model / name).touch()
            calls = []

            def text2token(phrases, **kwargs):
                calls.append(kwargs)
                return [["S", "AY1", "F", "ER0"] for _ in phrases]

            sherpa = types.SimpleNamespace(text2token=text2token,
                                           KeywordSpotter=lambda **kwargs: kwargs)
            with patch.dict(sys.modules, {"sherpa_onnx": sherpa}):
                spotter, keyword_file = wake_worker.make_spotter(model)
            try:
                self.assertEqual(calls[0]["tokens_type"], "phone+ppinyin")
                self.assertEqual(calls[0]["lexicon"], str(model / "en.phone"))
                self.assertIn("S AY1 F ER0", pathlib.Path(keyword_file).read_text(encoding="utf-8"))
                self.assertEqual(spotter["keywords_file"], keyword_file)
            finally:
                pathlib.Path(keyword_file).unlink()

    def test_audio_frame_is_bounded_and_error_code_is_sanitized(self):
        audio = wake_worker.make_wave([b"\x00\x00" * 16000])
        self.assertEqual(audio[:4], b"RIFF")
        self.assertEqual(wake_worker.error_code(OSError("private device name")), "INPUT_UNAVAILABLE")

    def test_command_capture_uses_existing_stream_and_speech_end(self):
        import numpy as np

        class Mic:
            calls = 0

            def read(self, frames):
                self.calls += 1
                amplitude = 2000 if self.calls <= 8 else 0
                return np.full((frames, 1), amplitude, dtype=np.int16), False

        mic = Mic()
        output = io.StringIO()
        with patch.object(wake_worker.sys, "stdout", output):
            wake_worker.capture_command(mic, deque([b"\x00\x00" * 1280], maxlen=18), stream_chunks=True)
        line = output.getvalue().strip()
        self.assertTrue(line.startswith("CHUNK "))
        self.assertGreater(output.getvalue().count("CHUNK "), 3)
        audio_line = output.getvalue().splitlines()[-1]
        self.assertTrue(audio_line.startswith("AUDIO 1280 "))
        with wave.open(io.BytesIO(base64.b64decode(audio_line.split(" ", 2)[2])), "rb") as recording:
            self.assertEqual(recording.getframerate(), 16000)
            self.assertGreater(recording.getnframes(), 1280)
        self.assertLess(mic.calls, wake_worker.MAX_COMMAND_BLOCKS)

    def test_brief_acknowledgement_tone_cannot_become_a_command(self):
        import numpy as np

        class Mic:
            calls = 0

            def read(self, frames):
                self.calls += 1
                return np.full((frames, 1), 3000 if self.calls <= 3 else 0, dtype=np.int16), False

        output = io.StringIO()
        with patch.object(wake_worker.sys, "stdout", output):
            wake_worker.capture_command(Mic(), deque(maxlen=18), stream_chunks=True)
        self.assertEqual(output.getvalue().strip(), "NO_SPEECH")

    def test_auto_prefers_matching_wasapi_endpoint_and_native_rate(self):
        class Audio:
            default = type("Defaults", (), {"device": (1, 2)})()

            @staticmethod
            def check_input_settings(**_):
                return None

            @staticmethod
            def query_devices():
                return [
                    {"name": "Other", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 44100},
                    {"name": "My Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 44100},
                    {"name": "My Mic", "hostapi": 1, "max_input_channels": 1, "default_samplerate": 48000},
                ]

            @staticmethod
            def query_hostapis():
                return [{"name": "MME"}, {"name": "Windows WASAPI"}]

        selected = wake_worker.resolve_input(Audio, None, None, None)
        self.assertEqual((selected["index"], selected["rate"]), (2, 48000))
        self.assertEqual(wake_worker.resolve_input(Audio, None, "My Mic", "MME")["index"], 1)
        with self.assertRaises(wake_worker.WakeWorkerError):
            wake_worker.resolve_input(Audio, None, "Absent", None)

        class WasapiUnavailable(Audio):
            @staticmethod
            def check_input_settings(**kwargs):
                if kwargs["device"] == 2:
                    raise ValueError("unsupported endpoint")

        self.assertEqual(wake_worker.resolve_input(WasapiUnavailable, None, None, None)["index"], 1)

    def test_native_rate_resampling_keeps_80ms_and_16khz_output(self):
        for rate in (44100, 48000):
            frames = wake_worker.input_frames(rate)
            self.assertEqual(frames, round(rate * 0.08))
            samples = (np.sin(np.arange(frames) * 2 * np.pi * 440 / rate) * 10000).astype(np.int16)
            output = wake_worker.resample_frame(samples[:, None], rate)
            self.assertEqual(len(output), 1280)
            self.assertGreater(np.max(np.abs(output)), 9000)

    def test_selector_does_not_accept_unbounded_or_control_text(self):
        self.assertEqual(wake_worker.decode_selector(base64.b64encode(b"Windows WASAPI").decode()), "Windows WASAPI")
        with self.assertRaises(wake_worker.WakeWorkerError):
            wake_worker.decode_selector(base64.b64encode(b"bad\nname").decode())

    def test_wake_and_command_share_one_native_rate_stream(self):
        class Mic:
            reads = 0

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self, frames):
                self.reads += 1
                self.last_frames = frames
                return np.full((frames, 1), 3000 if self.reads <= 2 else 0, dtype=np.int16), False

        mic = Mic()
        opens = []
        sd = types.SimpleNamespace(
            check_input_settings=lambda **kwargs: opens.append(("check", kwargs)),
            InputStream=lambda **kwargs: (opens.append(("open", kwargs)), mic)[1],
        )

        class Stream:
            count = 0
            decoded = False

            def accept_waveform(self, rate, frame):
                self.count += 1
                assert rate == 16000 and len(frame) == 1280

        class Spotter:
            def create_stream(self):
                return Stream()

            def is_ready(self, stream):
                return stream.count == 2 and not stream.decoded

            def decode_stream(self, stream):
                stream.decoded = True

            def get_result(self, stream):
                return "CYPHER"

        output = io.StringIO()
        with patch.dict(sys.modules, {"sounddevice": sd}), patch.object(wake_worker.sys, "stdout", output):
            wake_worker.listen(Spotter(), {"index": 15, "rate": 48000})
        self.assertEqual([name for name, _ in opens], ["check", "open"])
        self.assertEqual(opens[1][1]["samplerate"], 48000)
        self.assertEqual(mic.last_frames, 3840)
        self.assertIn("DEVICE 15 48000\nREADY\n", output.getvalue())
        self.assertIn("WAKE\nNO_SPEECH", output.getvalue())


if __name__ == "__main__":
    unittest.main()
