"""Quality checks for generated CPU-mode audio segments."""

import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_silence


def analyze_audio(audio_path: str = None, audio_segment=None) -> dict:
    audio = audio_segment if audio_segment is not None else AudioSegment.from_file(audio_path)
    duration_sec = len(audio) / 1000.0
    samples = np.array(audio.get_array_of_samples())
    if audio.channels > 1:
        samples = samples.reshape(-1, audio.channels).mean(axis=1)
    max_val = float(np.iinfo(samples.dtype).max)
    samples_norm = samples.astype(np.float64) / max_val
    rms = np.sqrt(np.mean(samples_norm ** 2))
    peak = np.max(np.abs(samples_norm))
    silence_ranges = detect_silence(audio, silence_thresh=-42, min_silence_len=50)
    total_silence_ms = sum(end - start for start, end in silence_ranges)

    leading = silence_ranges[0][1] / 1000.0 if silence_ranges and silence_ranges[0][0] == 0 else 0.0
    trailing = (len(audio) - silence_ranges[-1][0]) / 1000.0 if silence_ranges and silence_ranges[-1][1] >= len(audio) - 50 else 0.0
    return {
        "duration_sec": round(duration_sec, 3),
        "silence_ratio": round(total_silence_ms / len(audio), 4) if len(audio) else 0,
        "leading_silence_sec": round(leading, 3),
        "trailing_silence_sec": round(trailing, 3),
        "rms_db": round(20 * np.log10(max(rms, 1e-10)), 2),
        "peak_db": round(20 * np.log10(max(peak, 1e-10)), 2),
        "clipping_ratio": round(float(np.sum(np.abs(samples_norm) >= 0.99)) / len(samples_norm), 6) if len(samples_norm) else 0,
    }


def evaluate_segment_quality(text: str, audio_path: str = None, config: dict = None, audio_segment=None) -> dict:
    cfg = config or _default_config()
    text_chars = len(text)
    estimated_sec = text_chars / cfg["duration"]["vietnamese_chars_per_second"]
    expected_min = estimated_sec * cfg["duration"]["min_ratio"]
    expected_max = estimated_sec * cfg["duration"]["max_ratio"]
    metrics = analyze_audio(audio_path, audio_segment=audio_segment)
    issues = []
    duration = metrics["duration_sec"]
    silence = metrics["silence_ratio"]

    if duration <= 0:
        return _failed("ZERO_DURATION", "Generated audio has zero duration", metrics)
    if silence >= cfg["silence"]["full_silence_ratio"]:
        return _failed("FULL_SILENCE", "Generated audio is silent", metrics)
    if text_chars >= cfg["text"]["min_chars_for_short_audio_failed"] and duration < cfg["text"]["extremely_short_audio_sec"]:
        return _failed("EXTREMELY_SHORT_AUDIO", "Generated audio is too short", metrics)

    if duration < expected_min:
        issues.append(_issue("DURATION_TOO_SHORT", "Possible incomplete speech", {"duration_sec": duration, "expected_min_sec": round(expected_min, 2)}))
    if duration > expected_max:
        issues.append(_issue("DURATION_TOO_LONG", "Audio duration seems too long", {"duration_sec": duration, "expected_max_sec": round(expected_max, 2)}))
    if cfg["silence"]["warning_silence_ratio"] <= silence < cfg["silence"]["full_silence_ratio"]:
        issues.append(_issue("EXCESSIVE_SILENCE", "Silence detected", {"silence_ratio": silence}))
    if metrics["leading_silence_sec"] >= cfg["silence"]["leading_silence_warning_sec"]:
        issues.append(_issue("LONG_LEADING_SILENCE", "Long silence at the beginning", {"leading_silence_sec": metrics["leading_silence_sec"]}))
    if metrics["trailing_silence_sec"] >= cfg["silence"]["trailing_silence_warning_sec"]:
        issues.append(_issue("LONG_TRAILING_SILENCE", "Long silence at the end", {"trailing_silence_sec": metrics["trailing_silence_sec"]}))
    if metrics["rms_db"] < cfg["volume"]["low_rms_db"] or metrics["peak_db"] < cfg["volume"]["low_peak_db"]:
        issues.append(_issue("LOW_VOLUME", "Audio volume is low", {"rms_db": metrics["rms_db"], "peak_db": metrics["peak_db"]}))
    if metrics["clipping_ratio"] >= cfg["clipping"]["warning_ratio"]:
        issues.append(_issue("CLIPPING_DETECTED", "Possible clipping detected", {"clipping_ratio": metrics["clipping_ratio"]}))
    if text_chars > cfg["text"]["long_segment_chars"]:
        issues.append(_issue("TEXT_TOO_LONG", "Segment text is too long", {"text_chars": text_chars}))

    return {"status": "warning" if issues else "done", "issues": issues, "metrics": metrics, "can_export": True, "should_recommend_retry": bool(issues)}


def _failed(code: str, message: str, metrics: dict) -> dict:
    return {"status": "failed", "issues": [{"code": code, "severity": "failed", "message": message, "details": {}}], "metrics": metrics, "can_export": False, "should_recommend_retry": True}


def _issue(code: str, message: str, details: dict) -> dict:
    return {"code": code, "severity": "warning", "message": message, "details": details}


def _default_config() -> dict:
    return {
        "duration": {"vietnamese_chars_per_second": 13, "min_ratio": 0.55, "max_ratio": 1.8},
        "silence": {"full_silence_ratio": 0.98, "warning_silence_ratio": 0.45, "leading_silence_warning_sec": 1.0, "trailing_silence_warning_sec": 1.5},
        "volume": {"low_rms_db": -35, "low_peak_db": -18},
        "clipping": {"warning_ratio": 0.001},
        "text": {"long_segment_chars": 500, "min_chars_for_short_audio_failed": 30, "extremely_short_audio_sec": 0.5},
    }
