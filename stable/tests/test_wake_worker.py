import pathlib
import sys
import unittest


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
        self.assertIn('print("STOP" if result.endswith("_STOP") else "WAKE", flush=True)', source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.", source)
        self.assertNotIn("writeframes", source)


if __name__ == "__main__":
    unittest.main()
