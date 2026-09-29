"""Read-only offline check of the installed Sherpa KWS model's bundled WAV."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import wave


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, help="offline candidate model directory")
    args = parser.parse_args()
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        print("Wake model sample check unavailable.")
        return 2
    settings_path = Path(base) / "Cypher" / "CorePreview" / "host_config.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        model = args.model_dir if args.model_dir else Path(str(settings["wake_model_path"]))
        deps = Path(str(settings["wake_deps_path"]))
        sample = model / "test_wavs" / "0.wav"
        if not sample.is_file():
            sample = model / "test_wavs" / "en_0.wav"
        keywords = model / "test_wavs" / "test_keywords.txt"
        if not keywords.is_file():
            keywords = model / "test_wavs" / "keywords.txt"
        if not all(path.is_file() for path in (sample, keywords, model / "tokens.txt")):
            raise ValueError("missing sample")
        sys.path.insert(0, str(deps.resolve()))
        import numpy as np
        import sherpa_onnx

        def model_file(prefix: str) -> str:
            matches = sorted(path for path in model.glob(prefix + "*.onnx")
                             if ".int8." not in path.name)
            if not matches:
                raise ValueError("missing model")
            return str(matches[0])

        def sample_detected(keyword_path: Path) -> bool:
            spotter = sherpa_onnx.KeywordSpotter(
                tokens=str(model / "tokens.txt"),
                encoder=model_file("encoder-"),
                decoder=model_file("decoder-"),
                joiner=model_file("joiner-"),
                keywords_file=str(keyword_path), keywords_threshold=0.25,
                num_threads=1,
            )
            stream = spotter.create_stream()
            with wave.open(str(sample), "rb") as recording:
                if recording.getnchannels() != 1 or recording.getsampwidth() != 2:
                    raise ValueError("unsupported sample")
                rate = recording.getframerate()
                if rate != 16000:
                    raise ValueError("unexpected rate")
                while True:
                    raw = recording.readframes(1280)
                    if not raw:
                        break
                    frame = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
                    stream.accept_waveform(rate, frame)
                    while spotter.is_ready(stream):
                        spotter.decode_stream(stream)
                        if spotter.get_result(stream):
                            return True
            stream.accept_waveform(rate, np.zeros(16000, dtype=np.float32))
            while spotter.is_ready(stream):
                spotter.decode_stream(stream)
                if spotter.get_result(stream):
                    return True
            return False

        bundled = sample_detected(keywords)
        if (model / "bpe.model").is_file():
            pieces = sherpa_onnx.text2token(
                ["LIGHT UP"], tokens=str(model / "tokens.txt"),
                tokens_type="bpe", bpe_model=str(model / "bpe.model"),
            )
        else:
            pieces = sherpa_onnx.text2token(
                ["LIGHT UP"], tokens=str(model / "tokens.txt"),
                tokens_type="phone+ppinyin", lexicon=str(model / "en.phone"),
            )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", prefix="cypher-sample-",
                                         encoding="utf-8", delete=False) as temporary:
            temporary.write(" ".join(pieces[0]) + " :1.00 #0.25 @LIGHT_UP\n")
            generated_path = Path(temporary.name)
        try:
            generated = sample_detected(generated_path)
        finally:
            generated_path.unlink(missing_ok=True)
        print("Bundled keywords: " + ("DETECTED" if bundled else "MISSED"))
        print("Cypher-style keyword formatting: " + ("DETECTED" if generated else "MISSED"))
        return 0 if bundled and generated else 1
    except (OSError, ValueError, KeyError, ImportError):
        print("Wake model sample check unavailable.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
