"""Bounded local wake-word listener for Cypher.

Only READY, SIGNAL, WAKE, STOP, or ERROR markers leave stdout. No audio or ambient
transcript is logged, persisted, or sent over a network connection.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile


PHRASES = (
    "HELLO CYPHER", "HELLO CIPHER", "HEY CYPHER", "HEY CIPHER",
    "CYPHER", "CIPHER", "CYPHER STOP", "CIPHER STOP",
)


def make_spotter(model_dir: Path):
    import sherpa_onnx

    required = ("tokens.txt", "bpe.model")
    if not model_dir.is_dir() or any(not (model_dir / name).is_file() for name in required):
        raise RuntimeError("The local wake model is missing.")
    tokens = sherpa_onnx.text2token(
        list(PHRASES), tokens=str(model_dir / "tokens.txt"),
        tokens_type="bpe", bpe_model=str(model_dir / "bpe.model"),
    )
    keyword_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="cypher-wake-", delete=False,
        encoding="utf-8",
    )
    try:
        for phrase, pieces in zip(PHRASES, tokens):
            keyword_file.write(" ".join(pieces) + " @" + phrase.replace(" ", "_") + "\n")
        keyword_file.close()

        def model_file(prefix: str) -> str:
            candidates = sorted(
                path for path in model_dir.glob(prefix + "*.onnx")
                if ".int8." not in path.name
            )
            if not candidates:
                raise RuntimeError("A local wake model component is missing.")
            return str(candidates[0])

        spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(model_dir / "tokens.txt"),
            encoder=model_file("encoder-"),
            decoder=model_file("decoder-"),
            joiner=model_file("joiner-"),
            keywords_file=keyword_file.name,
            keywords_threshold=0.25,
            num_threads=1,
        )
        return spotter, keyword_file.name
    except Exception:
        keyword_file.close()
        os.unlink(keyword_file.name)
        raise


def listen(spotter) -> None:
    import numpy as np
    import sounddevice as sd

    stream = spotter.create_stream()
    signaled = False
    audible_frames = 0
    # Check the actual default device before announcing readiness.
    sd.check_input_settings(samplerate=16000, channels=1, dtype="int16")
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1280) as mic:
        print("READY", flush=True)
        while True:
            audio, _overflow = mic.read(1280)
            frame = np.asarray(audio[:, 0], dtype=np.float32)
            if not signaled:
                audible_frames = audible_frames + 1 if np.max(np.abs(frame)) >= 1000 else 0
                if audible_frames >= 2:
                    print("SIGNAL", flush=True)
                    signaled = True
            stream.accept_waveform(16000, frame / 32768.0)
            while spotter.is_ready(stream):
                spotter.decode_stream(stream)
                result = str(spotter.get_result(stream) or "")
                if result:
                    print("STOP" if result.endswith("_STOP") else "WAKE", flush=True)
                    return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--deps-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    keyword_file = None
    try:
        if not (args.deps_dir / "sherpa_onnx" / "__init__.py").is_file():
            raise RuntimeError("The isolated wake dependencies are missing.")
        sys.path.insert(0, str(args.deps_dir.resolve()))
        spotter, keyword_file = make_spotter(args.model_dir)
        if args.self_test:
            spotter.create_stream()
            import sounddevice as sd
            sd.check_input_settings(samplerate=16000, channels=1, dtype="int16")
            print("READY", flush=True)
        else:
            listen(spotter)
        return 0
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print("ERROR", flush=True)
        print(type(exc).__name__ + ": " + str(exc)[:240], file=sys.stderr)
        return 1
    finally:
        if keyword_file:
            try:
                os.unlink(keyword_file)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
