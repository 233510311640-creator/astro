"""Bounded, local-only transcription for Cypher voice drafts.

Serve mode loads Whisper once and reads length-framed in-memory WAV messages.
No audio or transcript is persisted or logged by this worker.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import sys
import struct
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


def load_model(model_directory: Path):
    if not model_directory.is_dir() or not (model_directory / "model.bin").is_file() or not (model_directory / "tokenizer.json").is_file():
        raise VoiceInputError("The configured local Whisper model is missing or incomplete.")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from faster_whisper import WhisperModel
    return WhisperModel(str(model_directory), device="cpu", compute_type="int8", local_files_only=True)


def transcribe(data: bytes, model_directory: Path, model=None) -> dict[str, str]:
    samples = read_pcm_wav(data)
    if not model_directory.is_dir() or not (model_directory / "model.bin").is_file() or not (model_directory / "tokenizer.json").is_file():
        raise VoiceInputError("The configured local Whisper model is missing or incomplete.")

    import numpy as np

    # Avoid asking a generative recognizer to invent words for near-silence.
    if float(np.sqrt(np.mean(np.square(samples)))) < 0.002:
        return {"status": "no_speech", "text": ""}

    if model is None:
        model = load_model(model_directory)
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


def read_exact(stream, count: int) -> bytes | None:
    chunks = []
    remaining = count
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def serve(model_directory: Path) -> int:
    try:
        model = load_model(model_directory)
    except Exception:
        print('{"status":"error","text":"","code":"MODEL_UNAVAILABLE"}', flush=True)
        return 1
    print("READY", flush=True)
    while True:
        header = read_exact(sys.stdin.buffer, 4)
        if header is None:
            return 0
        size = struct.unpack("<I", header)[0]
        if size < 44 or size > MAX_INPUT_BYTES:
            print('{"status":"error","text":"","code":"AUDIO_LIMIT"}', flush=True)
            return 1
        data = read_exact(sys.stdin.buffer, size)
        if data is None:
            return 1
        try:
            result = transcribe(data, model_directory, model)
        except Exception:
            result = {"status": "error", "text": "", "code": "TRANSCRIPTION_FAILED"}
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local bounded Cypher voice transcription")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 1
    if args.model is None:
        parser.error("--model is required")
    if args.serve:
        return serve(args.model)
    try:
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        result = transcribe(data, args.model)
    except (VoiceInputError, ImportError, OSError, RuntimeError) as exc:
        result = {"status": "error", "text": "", "message": str(exc)[:240]}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0 if result["status"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
