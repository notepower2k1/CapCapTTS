import os
import json
import uuid
import re
import asyncio
import csv
from pathlib import Path
from typing import Optional

import onnxruntime
import numpy as np
from pydub import AudioSegment

from piper import PiperVoice, PiperConfig
from piper.config import PhonemeType, SynthesisConfig

from config import PIPER_DIR, FFMPEG_DIR, OUTPUT_DIR, PIPER_SAMPLE_RATE, CROSS_FADE_MS, CUSTOM_DICT_DIR, setup_hf_env

AudioSegment.converter = str(FFMPEG_DIR / "ffmpeg.exe")
AudioSegment.ffprobe = str(FFMPEG_DIR / "ffprobe.exe")
os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")


_NORMALIZER_CACHE = {}

def invalidate_normalizer_cache() -> None:
    """Force the next normalized request to load the current custom dictionaries."""
    _NORMALIZER_CACHE.clear()

def normalize_vietnamese(text: str) -> str:
    try:
        from vietnormalizer import VietnameseNormalizer, normalizer as vn_mod

        custom_dir = CUSTOM_DICT_DIR
        combined_dir = custom_dir / "_combined"
        combined_dir.mkdir(parents=True, exist_ok=True)

        default_data = Path(vn_mod.__file__).parent / "data"

        cache_key = "combined"
        if cache_key not in _NORMALIZER_CACHE:
            for name, key_col in [("acronyms.csv", "acronym"), ("non-vietnamese-words.csv", "original")]:
                target = combined_dir / name
                src = default_data / name

                entries = {}
                if src.exists():
                    for row in csv.DictReader(open(src, encoding="utf-8", newline="")):
                        k = (row.get(key_col) or "").strip().lower()
                        if k:
                            entries[k] = row

                custom_file = custom_dir / name
                if custom_file.exists():
                    for row in csv.DictReader(open(custom_file, encoding="utf-8", newline="")):
                        k = (row.get(key_col) or "").strip().lower()
                        if k:
                            entries[k] = row

                rows = list(entries.values())
                rows.sort(key=lambda r: len(r.get(key_col, "") or ""), reverse=True)
                fieldnames = list(rows[0].keys()) if rows else [key_col, "transliteration"]
                with open(target, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    w.writerows(rows)

            normalizer = VietnameseNormalizer(data_dir=str(combined_dir))

            custom_acro = custom_dir / "acronyms.csv"
            if custom_acro.exists():
                for row in csv.DictReader(open(custom_acro, encoding="utf-8", newline="")):
                    k = (row.get("acronym") or "").strip().lower()
                    v = (row.get("transliteration") or "").strip()
                    if k and v:
                        normalizer.non_vietnamese_map[k] = v
                normalizer.non_vietnamese_map = dict(
                    sorted(normalizer.non_vietnamese_map.items(), key=lambda x: len(x[0]), reverse=True)
                )
                normalizer._build_replacement_dict()

            _NORMALIZER_CACHE[cache_key] = normalizer
        else:
            normalizer = _NORMALIZER_CACHE[cache_key]

        return normalizer.normalize(text)

    except ImportError:
        return text


def clean_text(text: str) -> str:
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\b([A-Z]+)\b', lambda m: m.group(1).capitalize() if len(m.group(1)) > 2 else m.group(0), text)
    text = re.sub(r'([.,!?;:])\1+', r'\1', text)
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'([.,!?;:])(?!\s)(?=[^\s])', r'\1 ', text)
    return text.strip()


def chunk_text_sentences(text: str, max_chars: int = 0) -> list[str]:
    return _chunk_hybrid(text, max_chars)

# ─── Hybrid chunking (protect → sentence → merge → split) ───

_PROTECT_TOKEN_RE = re.compile(
    r'(https?://[^\s]+)'
    r'|([\w.+-]+@[\w-]+\.[\w.]+)'
    r'|(\b\d+\.\d+(?:%|x|X)?\b)'
    r'|(\bv?\d+(?:\.\d+)+\b)'
)

_CHUNK_ENGINE_PRESETS = {
    "low":    {"min_chars": 60,  "target_chars": 140, "max_chars": 240, "hard_max": 320},
    "medium": {"min_chars": 60,  "target_chars": 140, "max_chars": 240, "hard_max": 320},
    "high":   {"min_chars": 80,  "target_chars": 180, "max_chars": 320, "hard_max": 420},
}


def _protect_tokens(text: str):
    placeholders = {}
    def _replace(m):
        key = f"__P{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key
    return _PROTECT_TOKEN_RE.sub(_replace, text), placeholders


def _restore_tokens(text: str, placeholders: dict) -> str:
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def _split_long_chunk(text: str, limit: int) -> list[str]:
    parts = re.split(r'(?<=[;:])\s+', text)
    if len(parts) > 1 and all(len(p) <= limit for p in parts):
        return [p.strip() for p in parts if p.strip()]
    parts = re.split(r'(?<=,)\s+', text)
    if len(parts) > 1 and all(len(p) <= limit for p in parts):
        return [p.strip() for p in parts if p.strip()]
    result = []
    remaining = text
    while len(remaining) > limit:
        fwd = remaining.rfind(' ', 0, limit + 1)
        bwd = remaining.find(' ', limit)
        cut = fwd if fwd > limit // 2 else (bwd if bwd > 0 else limit)
        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        result.append(remaining)
    return result


def _chunk_hybrid(text: str, max_chars: int = 0, min_chars: int = 0,
                  target_chars: int = 0, hard_max_chars: int = 0) -> list[str]:
    if not text or not text.strip():
        return []
    if max_chars <= 0:
        max_chars = hard_max_chars or 320
    effective_min = min_chars or max(30, max_chars // 4)
    effective_target = target_chars or max_chars // 2

    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    protected, pmap = _protect_tokens(text)

    paragraphs = re.split(r'\n\s*\n', protected)

    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', para) if s.strip()]
        if not sentences:
            continue

        merged = []
        buf = ""
        for s in sentences:
            candidate = (buf + " " + s).strip() if buf else s
            if len(candidate) <= effective_target:
                buf = candidate
            else:
                if buf:
                    merged.append(buf)
                buf = s
        if buf:
            merged.append(buf)

        for i in range(len(merged)):
            m = merged[i]
            if len(m) < effective_min and i > 0:
                candidate = (merged[i - 1] + " " + m).strip()
                if len(candidate) <= max_chars:
                    merged[i - 1] = candidate
                    merged[i] = ""
        merged = [m for m in merged if m]

        for m in merged:
            if len(m) <= max_chars:
                chunks.append(m)
            else:
                chunks.extend(_split_long_chunk(m, max_chars))

        # Re-merge chunks that became too small after splitting
        i = 1
        while i < len(chunks):
            if len(chunks[i]) < effective_min:
                candidate = (chunks[i - 1] + " " + chunks[i]).strip()
                if len(candidate) <= max_chars:
                    chunks[i - 1] = candidate
                    chunks.pop(i)
                    continue
            i += 1

    if pmap:
        chunks = [_restore_tokens(c, pmap) for c in chunks]
    return chunks if chunks else [text]


def get_chunk_config(engine_type: str) -> dict:
    """Return (min_chars, target_chars, max_chars, hard_max) for an engine."""
    return dict(_CHUNK_ENGINE_PRESETS.get(engine_type, _CHUNK_ENGINE_PRESETS["low"]))


def merge_audio_segments(segments: list[AudioSegment], crossfade_ms: int = CROSS_FADE_MS) -> AudioSegment:
    if not segments:
        return AudioSegment.silent(duration=0)
    result = segments[0]
    for seg in segments[1:]:
        result = result.append(seg, crossfade=crossfade_ms)
    return result


class PiperEngine:
    def __init__(self):
        self._voices: dict[str, PiperVoice] = {}
        p_new = PIPER_DIR.parent / "piper-new"
        if p_new.exists() and any(p_new.glob("*.onnx")):
            self._models_dir = p_new
        else:
            self._models_dir = PIPER_DIR
        self._meta = self._load_meta()

    def _load_meta(self) -> dict:
        meta = {}
        meta_file = PIPER_DIR / "voices.json"
        if meta_file.exists():
            try:
                for entry in json.loads(meta_file.read_text(encoding="utf-8")):
                    vid = Path(entry.get("audio_path", "")).stem
                    meta[vid] = entry
            except Exception:
                pass
        return meta

    def _config_path(self, model_path: Path) -> Path | None:
        """Use the single shared Piper config for every ONNX voice."""
        shared = self._models_dir / "config.json"
        if shared.exists():
            return shared
        return None

    def list_voices(self, include_rate=False) -> list[dict]:
        voices = []
        for f in sorted(self._models_dir.glob("*.onnx")):
            voice_id = f.stem
            if self._config_path(f):
                m = self._meta.get(voice_id, {})
                label = m.get("name", voice_id.replace("_", " ").title())
                v = {"id": voice_id, "label": label, "engine": "piper", "gender": m.get("gender", ""), "description": m.get("description", "")}
                if include_rate:
                    v["rate"] = 18
                voices.append(v)
        return voices

    def _load_voice(self, voice_id: str) -> PiperVoice:
        if voice_id in self._voices:
            return self._voices[voice_id]
        onnx_path = self._models_dir / f"{voice_id}.onnx"
        json_path = self._config_path(onnx_path)
        if not onnx_path.exists() or not json_path:
            raise ValueError(f"Voice '{voice_id}' not found")
        session = onnxruntime.InferenceSession(str(onnx_path))
        with open(json_path, encoding="utf-8") as f:
            piper_cfg = PiperConfig.from_dict(json.load(f))
        voice = PiperVoice(session, piper_cfg)
        self._voices[voice_id] = voice
        return voice

    def synthesize(self, text: str, voice_id: str, speed: float = 1.0) -> AudioSegment:
        voice = self._load_voice(voice_id)
        syn_cfg = SynthesisConfig(
            noise_scale=0.667,
            length_scale=max(0.5, min(2.0, 1.0 / speed)),
            noise_w_scale=0.8,
        )
        segments = []
        for chunk in voice.synthesize(text, syn_cfg):
            seg = AudioSegment(
                chunk.audio_int16_bytes,
                frame_rate=chunk.sample_rate,
                sample_width=chunk.sample_width,
                channels=chunk.sample_channels,
            )
            segments.append(seg)
        return merge_audio_segments(segments)



VIENEU_VOICE_META = {
    "Minh Đức": {
        "name": "Minh Đức",
        "gender": "male",
        "desc": "Nam · Miền Bắc · Phong cách tin tức, phóng sự",
    },
    "Phạm Tuyên": {
        "name": "Phạm Tuyên",
        "gender": "male",
        "desc": "Nam · Miền Bắc · Trầm ấm, đối thoại tự nhiên",
    },
    "Thái Sơn": {
        "name": "Thái Sơn",
        "gender": "male",
        "desc": "Nam · Miền Nam · Phong cách kể chuyện, podcast",
    },
    "Xuân Vĩnh": {
        "name": "Xuân Vĩnh",
        "gender": "male",
        "desc": "Nam · Miền Nam · Giọng ấm, dẫn chuyện tự nhiên",
    },
    "Thanh Bình": {
        "name": "Thanh Bình",
        "gender": "male",
        "desc": "Nam · Miền Bắc · Truyền cảm, kể chuyện, sách nói",
    },
    "Trúc Ly": {
        "name": "Trúc Ly",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Giọng trẻ, nhẹ nhàng, tự nhiên",
    },
    "Ngọc Linh": {
        "name": "Ngọc Linh",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Phong cách kể chuyện, diễn cảm",
    },
    "Đoan Trang": {
        "name": "Đoan Trang",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Trong trẻo, đối thoại tự nhiên",
    },
    "Mai Anh": {
        "name": "Mai Anh",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Dõng dạc, phong cách bản tin",
    },
    "Thục Đoan": {
        "name": "Thục Đoan",
        "gender": "female",
        "desc": "Nữ · Miền Nam · Ngọt ngào, kể chuyện, radio",
    },
    "Minh Triết": {
        "name": "Minh Triết",
        "gender": "male",
        "desc": "Nam · Miền Nam · Chững chạc, đọc tin tức, thời sự",
    },
    "Thùy Dung": {
        "name": "Thùy Dung",
        "gender": "female",
        "desc": "Nữ · Miền Nam · Lưu loát, đọc tin tức, phóng sự",
    },
    "Quang Sơn": {
        "name": "Quang Sơn",
        "gender": "male",
        "desc": "Nam · Miền Trung · Giọng miền Trung ấm áp, tự nhiên",
    },
    "Ngọc Trân": {
        "name": "Ngọc Trân",
        "gender": "female",
        "desc": "Nữ · Miền Trung · Dịu dàng, giọng Trung truyền cảm",
    },
    "Mỹ Duyên": {
        "name": "Mỹ Duyên",
        "gender": "female",
        "desc": "Nữ · Miền Nam · Đọc truyện, sâu lắng, audiobook",
    },
    "Quỳnh Anh": {
        "name": "Quỳnh Anh",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Đọc truyện, diễn cảm, tâm sự",
    },
    "Đức Trí": {
        "name": "Đức Trí",
        "gender": "male",
        "desc": "Nam · Miền Nam · Trầm hùng, đọc truyện, thuyết minh",
    },
    "Kim Thanh": {
        "name": "Kim Thanh",
        "gender": "female",
        "desc": "Nữ · Miền Nam · Diễn cảm, đọc truyện, tiểu thuyết",
    },
    "Ngọc Huyền": {
        "name": "Ngọc Huyền",
        "gender": "female",
        "desc": "Nữ · Miền Bắc · Giọng đọc tự nhiên, đời thường",
    },
    "Adam": {
        "name": "Adam",
        "gender": "male",
        "desc": "Nam · Miền Nam · Giọng trẻ, năng động, tự nhiên",
    }
}

class VieneuEngine:
    def __init__(self):
        self._model = None
        self._preset_voices = []
        self._loaded = False

    def load(self, progress_callback=None):
        if self._loaded and self._model is not None:
            return
        if progress_callback:
            progress_callback("Loading VieNeu ONNX models...", 30)
        setup_hf_env()
        from vieneu import Vieneu
        self._model = Vieneu(backend="onnx")
        if progress_callback:
            progress_callback("Reading preset voices...", 80)
        raw = self._model.list_preset_voices()
        res = []
        for full_name, vid in raw:
            meta = VIENEU_VOICE_META.get(vid)
            if meta:
                display_name = meta["name"]
                gender = meta["gender"]
                desc = meta["desc"]
            else:
                parts = [p.strip() for p in full_name.split("—")]
                display_name = parts[0] if parts else vid
                desc = parts[1] if len(parts) > 1 else full_name
                gender = "female" if "Nữ" in full_name else "male"
            res.append({
                "id": vid,
                "label": display_name,
                "engine": "vieneu",
                "gender": gender,
                "description": desc,
                "rate": 20,
                "is_preset": True,
            })
        self._preset_voices = res
        self._loaded = True
        if progress_callback:
            progress_callback("Loaded", 100)

    def list_voices(self, include_rate=False) -> list[dict]:
        if not self._loaded:
            return []
        if not self._preset_voices:
            self.load()

        # 1. Preset voices
        result = []
        for p in self._preset_voices:
            item = dict(p)
            if include_rate:
                item["rate"] = 20
            result.append(item)

        # 2. Cloned voices from shared voices_dir
        from config import get_voices_dir
        vdir = get_voices_dir()
        meta_file = vdir / "voices.json"
        if meta_file.exists():
            import json
            try:
                entries = json.loads(meta_file.read_text(encoding="utf-8"))
                for e in entries:
                    vid = Path(e.get("audio_path", "")).stem
                    item = {
                        "id": vid,
                        "label": e.get("name", vid.replace("_", " ").title()),
                        "engine": "vieneu",
                        "gender": e.get("gender", "male"),
                        "description": e.get("description", ""),
                        "is_clone": True,
                    }
                    if include_rate:
                        item["rate"] = 20
                    result.append(item)
            except Exception as err:
                print(f"Error reading custom voices for Vieneu: {err}")
        return result

    def synthesize(self, text: str, voice_id: str, speed: float = 1.0, ref_audio: str = None, ref_text: str = None) -> AudioSegment:
        if not self._loaded or self._model is None:
            raise RuntimeError("VieNeu-TTS model is not loaded. Please load it first in Resources -> Load Models.")
        m = self._model

        # Check if voice_id is preset or custom clone
        preset_ids = {p["id"] for p in self._preset_voices}
        if voice_id in preset_ids:
            audio_data = m.infer(text, voice=voice_id)
        else:
            from config import get_voices_dir
            vdir = get_voices_dir()
            actual_audio = ref_audio
            actual_text = ref_text
            if not actual_audio:
                for ext in (".wav", ".mp3"):
                    p = vdir / f"{voice_id}{ext}"
                    if p.exists():
                        actual_audio = str(p)
                        break
            if not actual_text:
                meta_file = vdir / "voices.json"
                if meta_file.exists():
                    import json
                    try:
                        entries = json.loads(meta_file.read_text(encoding="utf-8"))
                        for e in entries:
                            if Path(e.get("audio_path", "")).stem == voice_id:
                                actual_text = e.get("text_ref", "")
                                break
                    except Exception:
                        pass
            if not actual_audio:
                audio_data = m.infer(text, voice="Adam")
            else:
                audio_data = m.infer(text, ref_audio=actual_audio, ref_text=actual_text)

        import io
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, audio_data, 48000, format='WAV')
        buf.seek(0)
        seg = AudioSegment.from_file(buf, format='wav')

        if speed != 1.0 and 0.5 <= speed <= 2.0:
            new_frame_rate = int(seg.frame_rate * speed)
            seg = seg._spawn(seg.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(seg.frame_rate)

        return seg


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create(self, text: str, voice_mode: str, voice_id: str, output_format: str = "mp3", normalize: bool = False, clean: bool = False, normalize_audio: bool = True, speed: float = 1.0, pitch: float = 0.0, volume: float = 0.0, split_segments: bool = True, split_mode: str = "default") -> str:
        task_id = uuid.uuid4().hex[:12]
        # Chunking is mode-dependent and is performed once by _run_generation.
        chunks = []
        async with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id, "text": text, "voice_mode": voice_mode,
                "voice_id": voice_id, "output_format": output_format,
                "normalize": normalize, "clean": clean, "normalize_audio": normalize_audio,
                "speed": speed, "pitch": pitch, "volume": volume,
                "split_segments": split_segments, "split_mode": split_mode,
                "chunks": chunks, "status": "pending", "progress": 0,
                "stage": "queued", "audio_url": None, "duration": None, "error": None,
            }
        return task_id

    async def update(self, task_id: str, **kwargs):
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(kwargs)

    async def get(self, task_id: str) -> Optional[dict]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_chunk(self, task_id: str, chunk_index: int, **kwargs):
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and chunk_index < len(task["chunks"]):
                task["chunks"][chunk_index].update(kwargs)

    async def set_chunk_audio(self, task_id: str, chunk_index: int, audio_path: str, duration: float = 0):
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and chunk_index < len(task["chunks"]):
                task["chunks"][chunk_index]["audio_path"] = audio_path
                task["chunks"][chunk_index]["duration"] = duration
                task["chunks"][chunk_index]["status"] = "done"

    async def set_chunk_audio_with_quality(self, task_id: str, chunk_index: int, audio_path: str, duration: float, quality: dict):
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and chunk_index < len(task["chunks"]):
                chunk = task["chunks"][chunk_index]
                chunk["audio_path"] = audio_path
                chunk["duration"] = duration
                chunk["issues"] = quality["issues"]
                chunk["quality_metrics"] = quality["metrics"]
                chunk["can_export"] = quality["can_export"]
                chunk["should_recommend_retry"] = quality["should_recommend_retry"]
                if quality["status"] == "failed":
                    chunk["status"] = "error"
                    chunk["error"] = quality["issues"][0]["message"] if quality["issues"] else "Quality check failed"
                    chunk["warning"] = False
                elif quality["status"] == "warning":
                    chunk["status"] = "done"
                    chunk["warning"] = True
                else:
                    chunk["status"] = "done"
                    chunk["warning"] = False

    async def set_chunk_error(self, task_id: str, chunk_index: int, error: str):
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and chunk_index < len(task["chunks"]):
                task["chunks"][chunk_index]["status"] = "error"
                task["chunks"][chunk_index]["error"] = error

    async def recalc_progress(self, task_id: str, extra_pct: int = 0):
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task or not task["chunks"]:
                return
            total = len(task["chunks"])
            done = sum(1 for c in task["chunks"] if c["status"] == "done")
            pct = 5 + int(80 * (done / total)) + extra_pct
            task["progress"] = min(pct, 100)

    async def reset(self, task_id: str) -> bool:
        async with self._lock:
            return self._tasks.pop(task_id, None) is not None

    async def set_chunks(self, task_id: str, chunks: list[dict]) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["chunks"] = chunks
                return True
            return False
