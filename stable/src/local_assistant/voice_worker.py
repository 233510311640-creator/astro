"""Bounded, local-only batch transcription for Cypher voice drafts.

This worker is intentionally not wired into the resident host until the native
microphone capture and full end-to-end path have been verified. It reads one
PCM WAV message from stdin and returns one short JSON result on stdout.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import sys
import wave


MAX_INPUT_BYTES = 2_000_000
MAX_SECONDS = 20
MAX_TEXT_CHARS = 1200
SUPPORTED_RATES = frozenset({16000, 32000, 44100, 48000})


class VoiceInputError(ValueError):
    """The supplied in-memory audio does not meet the voice-input contract."""


def read_pcm_wav(data: bytes):
    """Return mono float32 samples at 16 kHz, without saving the input."""
    if not data or len(data) > MAX_INPUT_BYTES:
        raise VoiceInputError("Audio is empty or exceeds the 20-second input limit.")
    try:
        with wave.open(io.BytesIO(data), "rb") as recording:
            if recording.getcomptype() != "NONE" or recording.getnchannels() != 1:
                raise VoiceInputError("Only uncompressed mono microphone audio is accepted.")
            if recording.getsampwidth() != 2 or recording.getframerate() not in SUPPORTED_RATES:
                raise VoiceInputError("The microphone format is not supported.")
            rate = recording.getframerate()
            frames = recording.getnframes()
            if frames < rate // 4 or frames > rate * MAX_SECONDS:
                raise VoiceInputError("Record between 0.25 and 20 seconds of speech.")
            pcm = recording.readframes(frames)
            if len(pcm) != frames * 2:
                raise VoiceInputError("The microphone recording is incomplete.")
    except (EOFError, wave.Error) as exc:
        raise VoiceInputError("The microphone recording is not a valid PCM WAV stream.") from exc

    import numpy as np

    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    if rate != 16000:
        from scipy.signal import resample_poly
        from math import gcd

        divisor = gcd(rate, 16000)
        samples = resample_poly(samples, 16000 // divisor, rate // divisor).astype(np.float32)
    return samples


def transcribe(data: bytes, model_directory: Path) -> dict[str, str]:
    samples = read_pcm_wav(data)
    if not model_directory.is_dir() or not (model_directory / "model.bin").is_file() or not (model_directory / "tokenizer.json").is_file():
        raise VoiceInputError("The configured local Whisper model is missing or incomplete.")

    import numpy as np

    # Avoid asking a generative recognizer to invent words for near-silence.
    if float(np.sqrt(np.mean(np.square(samples)))) < 0.002:
        return {"status": "no_speech", "text": ""}

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from faster_whisper import WhisperModel

    model = WhisperModel(str(model_directory), device="cpu", compute_type="int8", local_files_only=True)
    segments, _ = model.transcribe(
        samples,
        language="en",
        task="transcribe",
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        word_timestamps=False,
    )
    pieces: list[str] = []
    length = 0
    for segment in segments:
        piece = " ".join(segment.text.split())
        if not piece:
            continue
        allowed = MAX_TEXT_CHARS - length - (1 if pieces else 0)
        if allowed <= 0:
            break
        piece = piece[:allowed]
        pieces.append(piece)
        length += len(piece) + (1 if len(pieces) > 1 else 0)
    text = " ".join(pieces).strip()
    return {"status": "ok" if text else "no_speech", "text": text}


def self_test() -> bool:
    import struct

    with io.BytesIO() as stream:
        with wave.open(stream, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(16000)
            recording.writeframes(struct.pack("<8000h", *([0] * 8000)))
        valid = stream.getvalue()
    try:
        if len(read_pcm_wav(valid)) != 8000:
            return False
        for bad in (b"", b"not a wave", valid + b"0" * MAX_INPUT_BYTES):
            try:
                read_pcm_wav(bad)
            except VoiceInputError:
                pass
            else:
                return False
    except Exception:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local bounded Cypher voice transcription")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 1
    if args.model is None:
        parser.error("--model is required")
    try:
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        result = transcribe(data, args.model)
    except (VoiceInputError, ImportError, OSError, RuntimeError) as exc:
        result = {"status": "error", "text": "", "message": str(exc)[:240]}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0 if result["status"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
