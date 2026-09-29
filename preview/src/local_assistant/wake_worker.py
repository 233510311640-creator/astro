"""Local wake and post-wake capture on one continuous input stream.

Only bounded status markers and post-wake WAV bytes leave stdout. The short
pre-roll remains in memory and is discarded unless the local keyword fires.
"""

from __future__ import annotations

import argparse
import base64
from collections import deque
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import wave


PHRASES = (
    "HELLO CYPHER", "HELLO CIPHER", "HEY CYPHER", "HEY CIPHER",
    "CYPHER", "CIPHER", "CYPHER STOP", "CIPHER STOP",
)
SAMPLE_RATE = 16000
BLOCK_FRAMES = 1280
PRE_ROLL_BLOCKS = 18
MAX_COMMAND_BLOCKS = 150
SILENCE_BLOCKS = 11
MAX_AUDIO_BYTES = 44 + (PRE_ROLL_BLOCKS + MAX_COMMAND_BLOCKS) * BLOCK_FRAMES * 2
MAX_DEVICE_NAME = 200


class WakeWorkerError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def phrase_lines(tokens, score: float = 1.0, threshold: float = 0.25):
    """Sherpa keyword syntax with bounded, configurable phrase tuning."""
    if not (0.5 <= score <= 2.0 and 0.15 <= threshold <= 0.8):
        raise WakeWorkerError("TUNING_INVALID")
    for phrase, pieces in zip(PHRASES, tokens):
        tuned = phrase not in ("CYPHER STOP", "CIPHER STOP")
        yield (" ".join(pieces) +
               " :{:.2f} #{:.2f} @".format(score if tuned else 1.0, threshold if tuned else 0.25) +
               phrase.replace(" ", "_"))


def make_spotter(model_dir: Path, score: float = 1.0, threshold: float = 0.25):
    import sherpa_onnx

    if not model_dir.is_dir() or not (model_dir / "tokens.txt").is_file():
        raise WakeWorkerError("MODEL_MISSING")
    if (model_dir / "en.phone").is_file():
        tokens = sherpa_onnx.text2token(
            list(PHRASES), tokens=str(model_dir / "tokens.txt"),
            tokens_type="phone+ppinyin", lexicon=str(model_dir / "en.phone"),
        )
    elif (model_dir / "bpe.model").is_file():
        tokens = sherpa_onnx.text2token(
            list(PHRASES), tokens=str(model_dir / "tokens.txt"),
            tokens_type="bpe", bpe_model=str(model_dir / "bpe.model"),
        )
    else:
        raise WakeWorkerError("MODEL_MISSING")
    if len(tokens) != len(PHRASES) or any(not pieces for pieces in tokens):
        raise WakeWorkerError("MODEL_MISSING")
    keyword_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="cypher-wake-", delete=False,
        encoding="utf-8",
    )
    try:
        for line in phrase_lines(tokens, score, threshold):
            keyword_file.write(line + "\n")
        keyword_file.close()

        def model_file(prefix: str) -> str:
            candidates = sorted(
                path for path in model_dir.glob(prefix + "*.onnx")
                if ".int8." not in path.name
            )
            if not candidates:
                raise WakeWorkerError("MODEL_MISSING")
            return str(candidates[0])

        spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(model_dir / "tokens.txt"),
            encoder=model_file("encoder-"),
            decoder=model_file("decoder-"),
            joiner=model_file("joiner-"),
            keywords_file=keyword_file.name,
            keywords_threshold=threshold,
            num_threads=1,
        )
        return spotter, keyword_file.name
    except Exception:
        keyword_file.close()
        os.unlink(keyword_file.name)
        raise


def make_wave(chunks: list[bytes]) -> bytes:
    pcm = b"".join(chunks)
    if len(pcm) > MAX_AUDIO_BYTES - 44:
        raise WakeWorkerError("AUDIO_LIMIT")
    with io.BytesIO() as output:
        with wave.open(output, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(SAMPLE_RATE)
            recording.writeframes(pcm)
        return output.getvalue()


def decode_selector(encoded: str | None) -> str | None:
    if not encoded:
        return None
    try:
        value = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise WakeWorkerError("DEVICE_INVALID") from exc
    if not value or len(value) > MAX_DEVICE_NAME or any(ord(char) < 32 for char in value):
        raise WakeWorkerError("DEVICE_INVALID")
    return value


def input_devices(sd) -> list[dict]:
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    return [
        {"index": index, "name": str(device["name"])[:MAX_DEVICE_NAME],
         "api": str(host_apis[device["hostapi"]]["name"])[:MAX_DEVICE_NAME],
         "rate": int(device["default_samplerate"])}
        for index, device in enumerate(devices)
        if device["max_input_channels"] > 0
    ]


def resolve_input(sd, index: int | None, name: str | None, api: str | None) -> dict:
    devices = input_devices(sd)
    if index is not None:
        matches = [device for device in devices if device["index"] == index]
    elif name:
        matches = [device for device in devices if device["name"] == name and
                   (api is None or device["api"] == api)]
    else:
        default = sd.default.device[0]
        matches = [device for device in devices if device["index"] == default]
        if matches:
            # Windows frequently exposes the same physical microphone through
            # MME, DirectSound and WASAPI. Prefer its WASAPI endpoint when the
            # user has not selected one explicitly.
            same_name = [device for device in devices if device["name"] == matches[0]["name"]]
            matches = same_name or matches
    if not matches:
        raise WakeWorkerError("DEVICE_NOT_FOUND")
    candidates = sorted(matches, key=lambda device: device["api"] != "Windows WASAPI")
    valid_rate = False
    for selected in candidates:
        if not 8000 <= selected["rate"] <= 96000:
            continue
        valid_rate = True
        try:
            sd.check_input_settings(device=selected["index"], samplerate=selected["rate"],
                                    channels=1, dtype="int16")
            return selected
        except (OSError, ValueError):
            if index is not None or (name and api):
                break  # an explicit choice must never silently change devices
    raise WakeWorkerError("INPUT_UNAVAILABLE" if valid_rate else "FORMAT_UNSUPPORTED")


def input_frames(rate: int) -> int:
    return round(rate * BLOCK_FRAMES / SAMPLE_RATE)


def resample_frame(audio, rate: int):
    """Convert an 80 ms native-rate mono block to 16 kHz for KWS and STT."""
    import numpy as np

    source = np.asarray(audio[:, 0], dtype=np.int16)
    if len(source) == BLOCK_FRAMES and rate == SAMPLE_RATE:
        return source
    if len(source) < 2:
        raise WakeWorkerError("FORMAT_UNSUPPORTED")
    positions = np.arange(BLOCK_FRAMES, dtype=np.float64) * rate / SAMPLE_RATE
    return np.interp(np.minimum(positions, len(source) - 1),
                     np.arange(len(source)), source).astype(np.int16)


def read_frame(mic, rate: int):
    audio, overflow = mic.read(input_frames(rate))
    if overflow:
        raise WakeWorkerError("INPUT_OVERFLOW")
    return resample_frame(audio, rate)


def capture_command(mic, pre_roll: deque[bytes], stream_chunks: bool = False,
                    input_rate: int = SAMPLE_RATE) -> None:
    """Record on the same open device, ending after speech plus quiet."""
    import numpy as np

    chunks = list(pre_roll)
    pre_roll_frames = len(chunks) * BLOCK_FRAMES
    heard_speech = False
    quiet = 0
    pending_post_wake: list[bytes] = []
    for index in range(MAX_COMMAND_BLOCKS):
        frame = read_frame(mic, input_rate)
        raw = frame.tobytes()
        chunks.append(raw)
        if stream_chunks and not heard_speech:
            pending_post_wake.append(raw)
        rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
        started_now = False
        # Ignore the brief local acknowledgement tone when deciding whether
        # the user issued a command. Audio is still retained for one-utterance
        # transcription; only the VAD decision is delayed.
        if index >= 5 and rms >= 600:
            if stream_chunks and not heard_speech:
                for buffered in pending_post_wake:
                    print("CHUNK " + base64.b64encode(buffered).decode("ascii"), flush=True)
                pending_post_wake.clear()
                started_now = True
            heard_speech = True
            quiet = 0
        elif heard_speech:
            quiet += 1
        if stream_chunks and heard_speech and not started_now:
            print("CHUNK " + base64.b64encode(raw).decode("ascii"), flush=True)
        if heard_speech and quiet >= SILENCE_BLOCKS and index >= 4:
            break
        if not heard_speech and index >= 49:
            break
    if not heard_speech:
        print("NO_SPEECH", flush=True)
        return
    print("AUDIO " + str(pre_roll_frames) + " " +
          base64.b64encode(make_wave(chunks)).decode("ascii"), flush=True)


def listen(spotter, selected: dict, stream_chunks: bool = False) -> None:
    import numpy as np
    import sounddevice as sd

    stream = spotter.create_stream()
    signaled = False
    audible_frames = 0
    pre_roll: deque[bytes] = deque(maxlen=PRE_ROLL_BLOCKS)
    device, rate = selected["index"], selected["rate"]
    frames = input_frames(rate)
    sd.check_input_settings(device=device, samplerate=rate, channels=1, dtype="int16")
    with sd.InputStream(device=device, samplerate=rate, channels=1,
                        dtype="int16", blocksize=frames) as mic:
        print("DEVICE " + str(device) + " " + str(rate), flush=True)
        print("READY", flush=True)
        silent_blocks = 0
        silent_reported = False
        while True:
            frame = read_frame(mic, rate)
            peak = int(np.max(np.abs(frame.astype(np.int32))))
            silent_blocks = silent_blocks + 1 if peak <= 10 else 0
            if silent_blocks >= 125 and not silent_reported:
                print("SILENT", flush=True)
                silent_reported = True
            pre_roll.append(frame.tobytes())
            if not signaled:
                audible_frames = audible_frames + 1 if peak >= 1000 else 0
                if audible_frames >= 2:
                    print("SIGNAL", flush=True)
                    signaled = True
            stream.accept_waveform(SAMPLE_RATE, frame.astype(np.float32) / 32768.0)
            while spotter.is_ready(stream):
                spotter.decode_stream(stream)
                result = str(spotter.get_result(stream) or "")
                if result:
                    if result.endswith("_STOP"):
                        print("STOP", flush=True)
                    else:
                        print("WAKE", flush=True)
                        capture_command(mic, pre_roll, stream_chunks, rate)
                    return


def probe_input(sd, selected: dict) -> None:
    import numpy as np

    rate = selected["rate"]
    frames = input_frames(rate)
    peak = 0
    sd.check_input_settings(device=selected["index"], samplerate=rate,
                            channels=1, dtype="int16")
    with sd.InputStream(device=selected["index"], samplerate=rate,
                        channels=1, dtype="int16", blocksize=frames) as mic:
        for _ in range(38):
            frame = read_frame(mic, rate)
            peak = max(peak, int(np.max(np.abs(frame.astype(np.int32)))))
    print("PROBE " + str(peak), flush=True)


def error_code(exc: Exception) -> str:
    if isinstance(exc, WakeWorkerError):
        return exc.code
    if isinstance(exc, ImportError):
        return "DEPENDENCY_MISSING"
    if isinstance(exc, (OSError, ValueError)):
        return "INPUT_UNAVAILABLE"
    return "WORKER_FAILURE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--deps-dir", type=Path, required=True)
    parser.add_argument("--device", type=int)
    parser.add_argument("--device-name-b64")
    parser.add_argument("--host-api-b64")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--probe-device", action="store_true")
    parser.add_argument("--score", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--stream-chunks", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    keyword_file = None
    try:
        if not (args.deps_dir / "sherpa_onnx" / "__init__.py").is_file():
            raise WakeWorkerError("DEPENDENCY_MISSING")
        sys.path.insert(0, str(args.deps_dir.resolve()))
        import sounddevice as sd
        name = decode_selector(args.device_name_b64)
        api = decode_selector(args.host_api_b64)
        if args.list_devices:
            print("DEVICES " + json.dumps(input_devices(sd), ensure_ascii=True), flush=True)
            return 0
        selected = resolve_input(sd, args.device, name, api)
        if args.probe_device:
            probe_input(sd, selected)
            return 0
        if args.model_dir is None:
            raise WakeWorkerError("MODEL_MISSING")
        spotter, keyword_file = make_spotter(args.model_dir, args.score, args.threshold)
        if args.self_test:
            spotter.create_stream()
            sd.check_input_settings(device=selected["index"], samplerate=selected["rate"],
                                    channels=1, dtype="int16")
            print("READY", flush=True)
        else:
            listen(spotter, selected, args.stream_chunks)
        return 0
    except Exception as exc:
        print("ERROR " + error_code(exc), flush=True)
        return 1
    finally:
        if keyword_file:
            try:
                os.unlink(keyword_file)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
