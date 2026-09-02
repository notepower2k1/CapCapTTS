import os
import re
import sys
import csv
import asyncio
import time
import io
import shutil
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Form, File, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydub import AudioSegment

import aiohttp
import aiofiles
from huggingface_hub import HfApi

from config import OUTPUT_DIR, CUSTOM_DICT_DIR, PIPER_DIR, MAX_TEXT_LENGTH, get_resource_dir, set_resource_dir, get_default_resource_dir, get_voices_dir, get_use_mirror, set_use_mirror
from tts_quality_checker import evaluate_segment_quality
from tts_engine import (
    PiperEngine, VieneuEngine, TaskManager,
    chunk_text_sentences, merge_audio_segments,
    normalize_vietnamese, invalidate_normalizer_cache, clean_text,
    _chunk_hybrid, get_chunk_config,
)


def _worker_count(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


PIPER_EXECUTOR = ThreadPoolExecutor(max_workers=_worker_count("PIPER_WORKERS", min(4, os.cpu_count() or 1)))
AUDIO_IO_EXECUTOR = ThreadPoolExecutor(max_workers=_worker_count("AUDIO_IO_WORKERS", 2))


def _synthesize_one(piper_engine, vieneu_engine, text: str, voice_mode: str, voice_id: str, speed: float = 1.0, normalize_audio: bool = True):
    if voice_mode in ("medium", "vieneu", "turbo"):
        if not voice_id or voice_id == "banmai":
            voice_id = "Adam"
        audio = vieneu_engine.synthesize(text, voice_id, speed=speed)
    else:
        audio = piper_engine.synthesize(text, voice_id, speed=speed)
    if normalize_audio:
        target = -20
        if audio.dBFS != float('-inf'):
            change = target - audio.dBFS
            audio = audio.apply_gain(change)
    return audio


PAUSE_FILE = CUSTOM_DICT_DIR / "_pause.json"
PAUSE_DEFAULTS = {"enabled": True, "pauses": {".": 0.4, ",": 0.2, ";": 0.3, ":": 0.3, "?": 0.4, "!": 0.4, "linebreak": 0.6}}


def _merge_pause_config(cfg: dict) -> dict:
    enabled = bool(cfg.get("enabled", True))
    pauses = dict(PAUSE_DEFAULTS["pauses"])
    pauses.update(cfg.get("pauses", {}))
    valid_keys = {".", ",", ";", ":", "?", "!", "linebreak"}
    validated_pauses = {k: max(0, float(v)) for k, v in pauses.items() if k in valid_keys}
    return {"enabled": enabled, "pauses": validated_pauses}


def _load_pause_config() -> dict:
    if PAUSE_FILE.exists():
        try:
            cfg = json.loads(PAUSE_FILE.read_text(encoding="utf-8"))
            if isinstance(cfg, dict) and "pauses" in cfg:
                pauses = cfg["pauses"]
                for k, v in PAUSE_DEFAULTS["pauses"].items():
                    if k not in pauses:
                        pauses[k] = v
                return _merge_pause_config(cfg)
        except Exception:
            pass
    return dict(PAUSE_DEFAULTS)


def _save_pause_config(cfg: dict):
    PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged = _merge_pause_config(cfg)
    PAUSE_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


CUSTOM_PAUSE_RE = re.compile(r'\[(\d+(?:\.\d+)?)\s*s\]', re.IGNORECASE)

def normalize_with_pause_protection(text: str) -> str:
    parts = CUSTOM_PAUSE_RE.split(text)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                result.append(normalize_vietnamese(part))
            else:
                result.append(part)
        else:
            result.append(f'[{part}s]')
    return ''.join(result)


def synthesize_with_pauses(piper_engine, vieneu_engine, voice_mode: str, text: str, voice_id: str, pause_cfg: dict, speed: float = 1.0, normalize_audio: bool = True):
    def _synth(t, vid):
        return _synthesize_one(piper_engine, vieneu_engine, t, voice_mode, vid, speed=speed, normalize_audio=normalize_audio)

    marker_parts = CUSTOM_PAUSE_RE.split(text)
    result = AudioSegment.silent(duration=0)
    for mi, mp in enumerate(marker_parts):
        if mi % 2 == 0:
            t = mp.strip()
            if not t:
                continue
            pauses = pause_cfg.get("pauses", {})
            _PAUSE_CHARS = {".", ",", ";", ":", "?", "!"}
            chars = "".join(re.escape(c) for c in pauses if c in _PAUSE_CHARS and pauses.get(c, 0) > 0)
            pause_re = re.compile(f"([{chars}])") if chars and pause_cfg.get("enabled", True) else None
            if not pause_re:
                result += _synth(t, voice_id)
            else:
                parts = [p for p in pause_re.split(t) if p.strip()]
                if not parts:
                    result += _synth(t, voice_id)
                else:
                    merged = []
                    for p in parts:
                        if p in pauses and merged and merged[-1] in pauses and merged[-1] == p:
                            continue
                        merged.append(p)
                    j = 0
                    while j < len(merged):
                        part = merged[j]
                        if part in pauses and pauses[part] > 0:
                            result += AudioSegment.silent(duration=int(pauses[part] * 1000))
                            j += 1
                            continue
                        if part.strip():
                            result += _synth(part, voice_id)
                        j += 1
                        if j < len(merged) and merged[j] in pauses and pauses[merged[j]] > 0:
                            result += AudioSegment.silent(duration=int(pauses[merged[j]] * 1000))
                            j += 1
        else:
            try:
                result += AudioSegment.silent(duration=int(float(mp) * 1000))
            except ValueError:
                pass
    if len(result) == 0:
        return _synth(text.strip() or " ", voice_id)
    return result


piper_engine = PiperEngine()
vieneu_engine = VieneuEngine()
task_manager = TaskManager()

_load_lock = asyncio.Lock()
_load_state = {
    "turbo": {"loaded": False, "loading": False, "progress": 0, "message": "", "error": False},
}

class LoadModelRequest(BaseModel):
    model: str





@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CapCap TTS (CPU)", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    path = request.url.path.lower()
    if path.endswith((".js", ".css", ".html")) or path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.post("/tts/load_model")
async def load_model(req: LoadModelRequest):
    if req.model in ("turbo", "vieneu", "medium"):
        if vieneu_engine._model is not None:
            _load_state["turbo"] = {"loaded": True, "loading": False, "progress": 100, "message": "Already loaded", "error": False}
            return {"status": "already_loaded"}
        async with _load_lock:
            if _load_state["turbo"]["loading"]:
                return {"status": "already_loading"}
            _load_state["turbo"] = {"loaded": False, "loading": True, "progress": 20, "message": "Loading VieNeu ONNX models...", "error": False}
        async def _load_turbo_bg():
            loop = asyncio.get_running_loop()
            def _cb(msg, pct):
                _load_state["turbo"] = {"loaded": False, "loading": True, "progress": pct, "message": msg, "error": False}
            try:
                await loop.run_in_executor(None, vieneu_engine.load, _cb)
                _load_state["turbo"] = {"loaded": True, "loading": False, "progress": 100, "message": "Loaded", "error": False}
            except Exception as e:
                _load_state["turbo"] = {"loaded": False, "loading": False, "progress": 0, "message": f"Error: {e}", "error": True}
        asyncio.create_task(_load_turbo_bg())
        return {"status": "loading"}
    raise HTTPException(400, "Model must be 'turbo'")


def task_dir(task_id: str) -> Path:
    d = OUTPUT_DIR / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


class TTSRequest(BaseModel):
    text: str
    voice_mode: str = "low"
    voice_id: str = "banmai"
    output_format: str = "mp3"
    normalize: bool = False
    clean: bool = False
    normalize_audio: bool = True
    speed: float = 1.0
    split_segments: bool = True
    split_mode: str = "default"


class ChunkRegenRequest(BaseModel):
    task_id: str
    chunk_index: int
    text: str | None = None
    voice_id: str | None = None


class MergeRequest(BaseModel):
    task_id: str
    output_format: str = "mp3"
    fade_edges: bool = True
    volume_match: bool = True
    crossfade: bool = True
    compressor: bool = True


class PauseConfigBody(BaseModel):
    config: dict


class DictEntry(BaseModel):
    key: str
    value: str


@app.get("/tts/voices")
async def list_voices():
    preset = piper_engine.list_voices(include_rate=True)
    vieneu_voices = vieneu_engine.list_voices() if vieneu_engine._loaded else []
    return {"low": preset, "turbo": vieneu_voices, "medium": vieneu_voices, "high": []}

@app.get("/tts/model_status")
async def model_status():
    is_loaded = bool(vieneu_engine._loaded and vieneu_engine._model is not None)
    _load_state["turbo"]["loaded"] = is_loaded
    return {
        "mode": "cpu",
        "gpu": {"available": False, "name": "", "vram_gb": 0, "cuda_version": ""},
        "turbo": dict(_load_state["turbo"]),
        "f5": {"loaded": False, "loading": False, "progress": 0, "message": "GPU only", "error": False},
        "omnivoice": {"loaded": False, "loading": False, "progress": 0, "message": "GPU only", "error": False},
        "models": {
            "low": {"loaded": True, "name": "Piper (22kHz)"},
            "turbo": {"loaded": is_loaded, "name": "VieNeu-TTS (48kHz ONNX)"},
            "medium": {"loaded": is_loaded, "name": "VieNeu-TTS (48kHz ONNX)"}
        }
    }


@app.get("/tts/voice_audio/{engine}/{voice_id}")
async def voice_audio(engine: str, voice_id: str):
    vdir = get_voices_dir()
    for ext in (".wav", ".mp3"):
        p = vdir / f"{voice_id}{ext}"
        if p.exists():
            return FileResponse(str(p), media_type="audio/mpeg" if p.suffix == ".mp3" else "audio/wav")
    raise HTTPException(404, "Audio not found")


@app.post("/tts/preview")
async def preview_tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Text is empty")

    if req.voice_mode in ("turbo", "vieneu") and not vieneu_engine._loaded:
        raise HTTPException(400, "VieNeu-TTS model not loaded. Load it first via Resources -> Load Models.")
    if req.clean:
        text = clean_text(text)
    if req.normalize:
        text = normalize_with_pause_protection(text)

    preview_text = text[:100]
    sentences = chunk_text_sentences(preview_text)
    preview_text = sentences[0] if sentences else preview_text[:80]

    voice_id = req.voice_id or "banmai"

    try:
        pause_cfg = _load_pause_config()
        loop = asyncio.get_running_loop()
        def _do():
            return synthesize_with_pauses(piper_engine, vieneu_engine, req.voice_mode, preview_text, voice_id, pause_cfg, speed=req.speed)
        audio = await loop.run_in_executor(PIPER_EXECUTOR, _do)
    except ValueError as e:
        raise HTTPException(404, str(e))

    preview_dir = OUTPUT_DIR / "_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_filename = f"preview_{int(time.time())}.wav"
    preview_path = preview_dir / preview_filename
    audio.export(str(preview_path), format="wav")
    return {
        "audio_url": f"/tts/download_file?path=_preview/{preview_filename}",
        "duration": round(len(audio) / 1000, 2),
    }


@app.post("/tts/generate")
async def generate_tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Text is empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(400, f"Text exceeds {MAX_TEXT_LENGTH} characters")

    task_id = await task_manager.create(
        text=text, voice_mode=req.voice_mode, voice_id=req.voice_id,
        output_format=req.output_format or "mp3", normalize=req.normalize,
        clean=req.clean, normalize_audio=req.normalize_audio, speed=req.speed,
        split_segments=req.split_segments, split_mode=req.split_mode if req.split_segments else "default",
    )

    asyncio.create_task(_run_generation(task_id))
    return {"task_id": task_id}


async def _run_generation(task_id: str):
    task = await task_manager.get(task_id)
    if not task:
        return
    text = task["text"]
    voice_id = task["voice_id"]
    output_format = task["output_format"]
    do_normalize = task.get("normalize")
    do_clean = task.get("clean")
    split_mode = task.get("split_mode", "default")

    try:
        await task_manager.update(task_id, status="processing", progress=0, stage="splitting")
        if do_clean:
            text = clean_text(text)

        cfg = get_chunk_config("low")
        if split_mode == "sentence":
            chunks = _chunk_hybrid(text, min_chars=10, target_chars=10, max_chars=cfg["hard_max"], hard_max_chars=cfg["hard_max"])
            is_new_para = [False] * len(chunks)
        elif split_mode == "paragraph":
            chunks = _chunk_hybrid(text, min_chars=cfg["min_chars"], target_chars=cfg["max_chars"], max_chars=cfg["hard_max"], hard_max_chars=cfg["hard_max"])
            is_new_para = [True] * len(chunks)
        elif split_mode == "custom":
            raw_blocks = re.split(r'\n\s*\n', text.strip())
            chunks = []
            for block in raw_blocks:
                block = block.strip()
                if not block:
                    continue
                if len(block) <= cfg["hard_max"]:
                    chunks.append(block)
                else:
                    from tts_engine import _split_long_chunk
                    chunks.extend(_split_long_chunk(block, cfg["hard_max"]))
            is_new_para = [True] * len(chunks)
        else:
            chunks = _chunk_hybrid(text, min_chars=cfg["min_chars"], target_chars=cfg["target_chars"], max_chars=cfg["max_chars"], hard_max_chars=cfg["hard_max"])
            is_new_para = []
            raw_paragraphs = re.split(r'\n\s*\n', text.strip())
            for p in raw_paragraphs:
                p = p.strip()
                if not p:
                    continue
                sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p) if s.strip()]
                if sents:
                    is_new_para.append(True)
                    is_new_para.extend([False] * (len(sents) - 1))
            is_new_para = is_new_para[:len(chunks)] if len(is_new_para) >= len(chunks) else is_new_para + [False] * (len(chunks) - len(is_new_para))

        if not chunks:
            await task_manager.update(task_id, status="error", error="No text to process")
            return

        if do_normalize:
            gen_texts = [normalize_with_pause_protection(c) for c in chunks]
        else:
            gen_texts = list(chunks)

        voice_id = task["voice_id"]

        chunks_data = []
        for i in range(len(chunks)):
            chunks_data.append({
                "index": i, "text": chunks[i], "gen_text": gen_texts[i],
                "new_paragraph": is_new_para[i] if i < len(is_new_para) else False,
                "status": "pending", "audio_path": None, "error": None,
                "voice_id": voice_id,
            })
        orig_texts = chunks
        await task_manager.set_chunks(task_id, chunks_data)

        await task_manager.update(task_id, status="processing", progress=5, stage="generating")
        loop = asyncio.get_running_loop()
        pause_cfg = _load_pause_config()

        spd = task.get("speed", 1.0)
        norm_audio = task.get("normalize_audio", True)

        vmode = task.get("voice_mode", "low")
        def _synth_one(i: int):
            seg = synthesize_with_pauses(piper_engine, vieneu_engine, vmode, gen_texts[i], voice_id, pause_cfg,
                speed=spd, normalize_audio=norm_audio)
            lb_pause = pause_cfg.get("pauses", {}).get("linebreak", 0)
            if i > 0 and chunks_data[i].get("new_paragraph") and lb_pause > 0:
                seg = AudioSegment.silent(duration=int(lb_pause * 1000)) + seg
            chunk_filename = f"chunk_{i}.wav"
            seg.export(str(task_dir(task_id) / chunk_filename), format="wav")
            quality = evaluate_segment_quality(orig_texts[i], None, None, seg)
            return i, chunk_filename, round(len(seg) / 1000, 3), quality

        for i in range(len(orig_texts)):
            await task_manager.update_chunk(task_id, i, status="processing")
        tasks = [loop.run_in_executor(PIPER_EXECUTOR, _synth_one, i) for i in range(len(orig_texts))]
        for coro in asyncio.as_completed(tasks):
            i, chunk_filename, chunk_dur, quality = await coro
            await task_manager.set_chunk_audio_with_quality(task_id, i,
                f"/tts/download_file?path={task_id}/{chunk_filename}", duration=chunk_dur, quality=quality)
            await task_manager.recalc_progress(task_id)

        await _save_segments_meta(task_id)
        await task_manager.update(task_id, status="chunks_done", progress=85, stage="chunks_done")

    except Exception as e:
        td = task_dir(task_id)
        if td.exists():
            for f in list(td.iterdir()):
                if f.name.startswith("chunk_"):
                    f.unlink()
        await task_manager.update(task_id, status="error", error=str(e))


@app.get("/tts/status/{task_id}")
async def get_status(task_id: str):
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "task_id": task["task_id"], "status": task["status"],
        "progress": task["progress"], "stage": task["stage"],
        "audio_url": task.get("audio_url"), "duration": task.get("duration"),
        "error": task.get("error"),
        "chunks": [
            {
                "index": c["index"], "text": c["text"],
                "gen_text": c.get("gen_text", c["text"]),
                "status": c["status"], "audio_url": c["audio_path"],
                "duration": c.get("duration", 0), "error": c.get("error"),
                "warning": c.get("warning", False),
                "issues": c.get("issues", []),
                "can_export": c.get("can_export", True),
                "should_recommend_retry": c.get("should_recommend_retry", False),
                "voice_id": c.get("voice_id", task.get("voice_id")),
            }
            for c in task.get("chunks", [])
        ],
    }


@app.post("/tts/regenerate_chunk")
async def regenerate_chunk(req: ChunkRegenRequest):
    task = await task_manager.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if req.chunk_index < 0 or req.chunk_index >= len(task["chunks"]):
        raise HTTPException(400, "Invalid chunk index")

    chunk_text = req.text if req.text else task["chunks"][req.chunk_index]["text"]
    chunk_gen_text = chunk_text
    if task.get("normalize"):
        chunk_gen_text = normalize_with_pause_protection(chunk_text)
    voice_id = req.voice_id or task["voice_id"]

    await task_manager.update_chunk(req.task_id, req.chunk_index, status="processing", text=chunk_text, gen_text=chunk_gen_text, voice_id=voice_id)

    try:
        pause_cfg = _load_pause_config()
        spd = task.get("speed", 1.0)
        na = task.get("normalize_audio", True)
        loop = asyncio.get_running_loop()
        vmode = task.get("voice_mode", "low")
        def _do(t=chunk_gen_text, vid=voice_id, pc=pause_cfg, s=spd, n_audio=na):
            return synthesize_with_pauses(piper_engine, vieneu_engine, vmode, t, vid, pc, speed=s, normalize_audio=n_audio)
        seg = await loop.run_in_executor(PIPER_EXECUTOR, _do)

        chunk_filename = f"chunk_{req.chunk_index}.wav"
        chunk_path = task_dir(req.task_id) / chunk_filename
        seg.export(str(chunk_path), format="wav")
        chunk_dur = round(len(seg) / 1000, 3)
        quality = await loop.run_in_executor(None, evaluate_segment_quality, chunk_text, None, None, seg)
        await task_manager.set_chunk_audio_with_quality(req.task_id, req.chunk_index, f"/tts/download_file?path={req.task_id}/{chunk_filename}", duration=chunk_dur, quality=quality)
        await task_manager.recalc_progress(req.task_id)

        qs = quality["status"]
        return {"chunk_index": req.chunk_index, "status": "done" if qs != "failed" else "error", "audio_url": f"/tts/download_file?path={req.task_id}/{chunk_filename}", "quality_status": qs, "issues": quality["issues"], "voice_id": voice_id}
    except Exception as e:
        await task_manager.set_chunk_error(req.task_id, req.chunk_index, str(e))
        raise HTTPException(500, str(e))


@app.post("/tts/merge")
async def merge_chunks(req: MergeRequest):
    task = await task_manager.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    chunks = task["chunks"]
    if not chunks:
        raise HTTPException(400, "No chunks to merge")

    for c in chunks:
        if c["status"] != "done":
            raise HTTPException(400, f"Chunk {c['index']} is not done yet")
        if not c.get("can_export", True):
            raise HTTPException(400, f"Chunk {c['index']} failed quality check and cannot be exported")

    output_format = req.output_format or "mp3"
    loop = asyncio.get_running_loop()
    td = task_dir(req.task_id)
    total_dur = 0

    def _load_post(filepath):
        seg = AudioSegment.from_file(filepath)
        if req.fade_edges:
            return seg.fade_in(8).fade_out(12)
        return seg

    chunk_paths = []
    for c in chunks:
        path = c["audio_path"].split("?path=")[-1]
        chunk_rel = path.split("/", 1)[-1] if "/" in path else path
        chunk_paths.append(str(td / chunk_rel))
    segments = await asyncio.gather(*[
        loop.run_in_executor(AUDIO_IO_EXECUTOR, _load_post, path) for path in chunk_paths
    ])

    srt_lines = []
    for idx, (c, seg) in enumerate(zip(chunks, segments)):
        chunk_dur = c.get("duration", round(len(seg) / 1000, 3))

        start_ms = int(total_dur * 1000)
        end_ms = int((total_dur + chunk_dur) * 1000)
        def _ms2srt(ms):
            h, rem = divmod(ms, 3600000)
            m, rem = divmod(rem, 60000)
            s, ms = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        txt = c["text"].strip().replace("\n", " ")
        srt_lines.append(f"{idx + 1}")
        srt_lines.append(f"{_ms2srt(start_ms)} --> {_ms2srt(end_ms)}")
        srt_lines.append(txt)
        srt_lines.append("")
        total_dur += chunk_dur

    # Mastering: optional volume match, crossfade, compressor
    def _finalize(segs):
        if req.volume_match and len(segs) > 1:
            avg_db = sum(s.dBFS for s in segs) / len(segs)
            segs = [s.apply_gain(avg_db - s.dBFS) for s in segs]
        cf_ms = 50 if req.crossfade else 0
        merged = merge_audio_segments(segs, crossfade_ms=cf_ms)
        if req.compressor:
            return merged.compress_dynamic_range(threshold=-20, ratio=2.0, attack=5, release=50)
        return merged
    merged = await loop.run_in_executor(AUDIO_IO_EXECUTOR, _finalize, segments)

    output_filename = f"final.{output_format}"
    output_path = td / output_filename
    def _write_outputs():
        if output_format.startswith("mp3"):
            merged.export(str(output_path), format="mp3", bitrate="320k")
        else:
            merged.export(str(output_path), format=output_format)
        (td / "final.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    await loop.run_in_executor(AUDIO_IO_EXECUTOR, _write_outputs)

    duration = round(len(merged) / 1000, 2)

    await task_manager.update(
        req.task_id, status="done", progress=100, stage="done",
        audio_url=f"/tts/download_file?path={req.task_id}/{output_filename}",
        duration=duration, done_at=asyncio.get_running_loop().time(),
    )

    await _save_history(req.task_id)

    return {"audio_url": f"/tts/download_file?path={req.task_id}/{output_filename}", "duration": duration}


# ─── Segment metadata (for on-the-fly SRT generation) ───

async def _save_segments_meta(task_id: str):
    import json
    td = task_dir(task_id)
    task = await task_manager.get(task_id)
    if task and task.get("chunks"):
        segments = [{"text": c.get("gen_text", c.get("text", "")), "duration": c.get("duration", 0)} for c in task["chunks"]]
        (td / "segments.json").write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")

def _load_segments_meta(task_id: str) -> list[dict]:
    import json
    meta_path = task_dir(task_id) / "segments.json"
    if not meta_path.exists():
        return []
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.get("/tts/download_file")
async def download_file(path: str = Query(...), format: str = Query("")):
    file_path = OUTPUT_DIR / path
    if not file_path.exists():
        raise HTTPException(404, "File not found")

    target_fmt = format.lower() if format else ""
    if target_fmt == "srt":
        task_id = path.split("/")[0]
        srt_path = OUTPUT_DIR / task_id / "final.srt"
        if srt_path.exists():
            return FileResponse(str(srt_path), media_type="text/plain", headers={"Content-Disposition": 'attachment; filename="subtitles.srt"'})
        segs = _load_segments_meta(task_id)
        if segs:
            srt_lines = []
            cum_ms = 0
            for idx, s in enumerate(segs):
                dur_ms = int(s.get("duration", 0) * 1000)
                if dur_ms <= 0:
                    continue
                def _ms2srt(ms):
                    h, rem = divmod(ms, 3600000)
                    m, rem = divmod(rem, 60000)
                    s, ms = divmod(rem, 1000)
                    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
                srt_lines.append(str(idx + 1))
                srt_lines.append(f"{_ms2srt(cum_ms)} --> {_ms2srt(cum_ms + dur_ms)}")
                srt_lines.append(s.get("text", f"Segment {idx + 1}"))
                srt_lines.append("")
                cum_ms += dur_ms
            content = "\n".join(srt_lines)
            return Response(content=content, media_type="text/plain", headers={"Content-Disposition": 'attachment; filename="subtitles.srt"'})
        raise HTTPException(404, "SRT file not found")

    src_fmt = file_path.suffix.lstrip(".")
    if not target_fmt or (target_fmt == "mp3_320" and src_fmt == "mp3"):
        # Serve original file (already 320k or no conversion needed)
        media_type = "audio/mpeg" if src_fmt == "mp3" else "audio/wav"
        return FileResponse(str(file_path), media_type=media_type)

    # Format conversion
    if target_fmt not in ("mp3", "mp3_320", "wav"):
        target_fmt = "mp3"
    loop = asyncio.get_running_loop()
    audio = await loop.run_in_executor(None, AudioSegment.from_file, str(file_path))
    buf = io.BytesIO()
    if target_fmt == "mp3_320":
        await loop.run_in_executor(None, lambda: audio.export(buf, format="mp3", bitrate="320k"))
    elif target_fmt == "mp3":
        await loop.run_in_executor(None, lambda: audio.export(buf, format="mp3", bitrate="128k"))
    else:
        await loop.run_in_executor(None, lambda: audio.export(buf, format=target_fmt))
    buf.seek(0)
    media_type = "audio/mpeg" if target_fmt in ("mp3", "mp3_320") else "audio/wav"
    return Response(content=buf.read(), media_type=media_type)


@app.post("/tts/reset/{task_id}")
async def reset_task(task_id: str):
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    td = task_dir(task_id)
    if td.exists():
        preserved = {}
        for name in ("final.mp3", "final.wav", "final.srt"):
            fp = td / name
            if fp.exists():
                preserved[name] = fp.read_bytes()
        for f in td.iterdir():
            if f.name.startswith("chunk_"):
                f.unlink()
    await task_manager.reset(task_id)
    return {"status": "reset", "preserved_files": list(preserved.keys())}


# ─── Resource Download ───

_hf_api = HfApi()
_dl_state = {}
_dl_lock = asyncio.Lock()
def get_hf_url(path: str, repo: str) -> str:
    base = "https://hf-mirror.com" if get_use_mirror() else "https://huggingface.co"
    return f"{base}/{repo}/resolve/main/{path}"

HF_URL = "https://huggingface.co/{repo}/resolve/main/{path}"

_PIPER_VOICES = [
    "adam1", "banmai", "chieuthanh", "cuc", "duyoryx3175", "lacphi",
    "maiphuong", "manhdung", "minhkhang", "minhquang", "minhthu",
    "mytam2", "mytam2794", "ngochuyen", "ngochuyennew", "ngocngan3701",
    "phuongtrang", "taian2", "taian4", "thanhphuong2", "thientam",
    "tranthanh3870", "vi_VN-vais1000-medium", "vietthao3886", "yannew",
]

_RESOURCE_DEFS = [
    {
        "id": "vieneu",
        "label": "VieNeu-TTS Model (Medium-Low · 48kHz ONNX)",
        "desc": "VieNeu v3 Turbo weights + MOSS Audio Tokenizer (~330MB)",
        "repo_id": "pnnbao-ump/VieNeu-TTS-v3-Turbo",
        "files": ["vieneu_models"],
        "local_dir": str(Path.home() / ".cache" / "huggingface" / "hub"),
    },
    {
        "id": "piper",
        "label": "Piper Voices (Low · CPU)",
        "repo_url": "https://huggingface.co/Hacht/CapCapResource/tree/main/piper-new",
        "repo_id": "Hacht/CapCapResource",
        "files": ["piper-new/voices.json", "piper-new/config.json"] + [f"piper-new/{v}.onnx" for v in _PIPER_VOICES],
        "local_dir": str(PIPER_DIR),
    },
    {
        "id": "f5_voices",
        "label": "Voice References",
        "desc": "Sample audio references for voice cloning (VieNeu, F5, OmniVoice)",
        "repo_url": "https://huggingface.co/Hacht/CapCapResource/tree/main/f5_voice",
        "repo_id": "Hacht/CapCapResource",
        "files": [f"f5_voice/{f}" for f in [
            "ai_hanh.mp3", "foxy.mp3", "lan.wav", "liam.mp3", "mai.mp3",
            "ngan_le.mp3", "ngan_nguyen.mp3", "nhat.mp3", "nhu.mp3",
            "nhung.mp3", "ninh_don.mp3", "phuong.mp3", "quynh_anh.mp3",
            "tham.mp3", "trieu_duong.mp3", "trung_caha.mp3", "tung.mp3",
        ]] + ["f5_voice/voices.json"],
        "local_dir": str(get_voices_dir()),
    },
]

def _local_path(local_dir: Path, repo_path: str) -> Path:
    parts = Path(repo_path).parts
    if parts[0] in ("piper", "piper-new", "f5_voice"):
        return local_dir / Path(*parts[1:])
    return local_dir / Path(repo_path)

async def _get_file_sizes(repo_id, paths):
    loop = asyncio.get_running_loop()
    def _fetch():
        try:
            infos = _hf_api.get_paths_info(repo_id, paths)
            return {i.path: i.size for i in infos if i}
        except Exception:
            return {}
    return await loop.run_in_executor(None, _fetch)



def _get_rdef_local_dir(rid: str) -> Path:
    rdir = get_resource_dir()
    if rid == "piper":
        p_new = rdir / "piper-new"
        if p_new.exists() and any(p_new.glob("*.onnx")):
            return p_new
        return rdir / "piper"
    elif rid in ("f5", "omnivoice"):
        return rdir / "f5"
    elif rid == "f5_voices":
        return rdir / "f5" / "f5_voice"
    elif rid == "vieneu":
        return rdir / "huggingface" / "hub"
    return rdir / rid

def _is_vieneu_downloaded() -> bool:
    candidates = [
        get_resource_dir() / "huggingface" / "hub",
        Path.home() / ".cache" / "huggingface" / "hub"
    ]
    for c in candidates:
        v3_dir = c / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo"
        moss_dir = c / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX"
        if v3_dir.exists() and any(v3_dir.rglob("*.onnx")) and moss_dir.exists() and any(moss_dir.rglob("*.onnx")):
            return True
    return False

async def _build_catalog():
    result = []
    for rdef in _RESOURCE_DEFS:
        rid = rdef["id"]
        if rid == "vieneu":
            downloaded = _is_vieneu_downloaded()
            async with _dl_lock:
                dl_info = _dl_state.get(rid, {"status": "done" if downloaded else "none", "progress": 100 if downloaded else 0, "current_file": "", "error": ""})
            result.append({
                "id": rid,
                "label": rdef["label"],
                "desc": rdef["desc"],
                "repo_url": "https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo",
                "target_dir": str(_get_rdef_local_dir("vieneu")),
                "total_files": 2,
                "existing_files": 2 if downloaded else 0,
                "total_size_mb": 330.0,
                "downloaded": downloaded,
                "status": dl_info["status"],
                "progress": dl_info["progress"],
                "current_file": dl_info["current_file"],
                "error": dl_info.get("error", ""),
            })
            continue
        sizes = await _get_file_sizes(rdef["repo_id"], rdef["files"])
        total_size = sum(sizes.values())
        size_mb = total_size / (1024 * 1024)
        local_dir = _get_rdef_local_dir(rid)
        existing = sum(1 for fp in rdef["files"] if _local_path(local_dir, fp).exists())
        async with _dl_lock:
            dl_info = _dl_state.get(rid, {"status":"none","progress":0,"current_file":"","error":""})
        result.append({
            "id": rid, "label": rdef["label"], "desc": rdef.get("desc", ""),
            "repo_url": rdef.get("repo_url", f"https://huggingface.co/{rdef['repo_id']}"),
            "target_dir": str(local_dir),
            "total_files": len(rdef["files"]), "existing_files": existing,
            "total_size_mb": round(size_mb, 1),
            "downloaded": existing == len(rdef["files"]),
            "status": dl_info["status"], "progress": dl_info["progress"],
            "current_file": dl_info["current_file"], "error": dl_info.get("error",""),
        })
    return result

async def _download_resource(rid: str):
    rdef = next((r for r in _RESOURCE_DEFS if r["id"] == rid), None)
    if not rdef:
        return
    local_dir = _get_rdef_local_dir(rid)
    repo_id = rdef["repo_id"]
    files = rdef["files"]
    sizes = await _get_file_sizes(repo_id, files)
    total_bytes = sum(sizes.values())
    downloaded_bytes = sum(sizes.get(fp,0) for fp in files if _local_path(local_dir, fp).exists())
    async with _dl_lock:
        _dl_state[rid] = {"status":"downloading","progress":0,"current_file":"","error":""}
    try:
        for fp in files:
            target = _local_path(local_dir, fp)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            url = get_hf_url(fp, repo_id)
            async with _dl_lock:
                _dl_state[rid]["current_file"] = fp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    async with aiofiles.open(str(target), "wb") as f:
                        while True:
                            chunk = await resp.content.read(65536)
                            if not chunk:
                                break
                            await f.write(chunk)
                            if total_bytes > 0:
                                async with _dl_lock:
                                    _dl_state[rid]["progress"] = int(downloaded_bytes * 100 / total_bytes)
        async with _dl_lock:
            _dl_state[rid] = {"status":"done","progress":100,"current_file":"","error":""}
    except Exception as e:
        async with _dl_lock:
            _dl_state[rid] = {"status":"error","progress":0,"current_file":"","error":str(e)}


# ─── Storage Settings ───

class SettingsRequest(BaseModel):
    resource_dir: str | None = None
    use_mirror: bool | None = None

@app.get("/tts/settings")
async def get_settings():
    return {
        "resource_dir": str(get_resource_dir()),
        "default_resource_dir": str(get_default_resource_dir()),
        "use_mirror": get_use_mirror(),
    }

@app.post("/tts/settings")
async def update_settings(req: SettingsRequest):
    if req.use_mirror is not None:
        set_use_mirror(req.use_mirror)
    if req.resource_dir:
        new_dir = set_resource_dir(req.resource_dir)
        os.environ["HF_HOME"] = str(new_dir / "huggingface")
        piper_engine._models_dir = new_dir / "piper"
        piper_engine._meta = piper_engine._load_meta()
    return {
        "status": "updated",
        "resource_dir": str(get_resource_dir()),
        "default_resource_dir": str(get_default_resource_dir()),
        "use_mirror": get_use_mirror(),
    }

@app.post("/tts/open_resource_folder")
async def open_resource_folder(req: dict):
    rid = req.get("resource_id", "")
    local_dir = _get_rdef_local_dir(rid)
    local_dir.mkdir(parents=True, exist_ok=True)
    import sys, subprocess
    if sys.platform == "win32":
        os.startfile(str(local_dir))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(local_dir)])
    else:
        subprocess.Popen(["xdg-open", str(local_dir)])
    return {"status": "opened", "path": str(local_dir)}

@app.post("/tts/open_folder")
async def open_folder(req: dict = None):
    p = get_resource_dir()
    p.mkdir(parents=True, exist_ok=True)
    import sys, subprocess
    if sys.platform == "win32":
        os.startfile(str(p))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])
    return {"status": "opened", "path": str(p)}

@app.get("/tts/resource_catalog")
async def resource_catalog():
    return await _build_catalog()

class StartDownloadRequest(BaseModel):
    resource_id: str

@app.post("/tts/start_download")
async def start_download(req: StartDownloadRequest):
    rid = req.resource_id
    rdef = next((r for r in _RESOURCE_DEFS if r["id"] == rid), None)
    if not rdef:
        raise HTTPException(400, f"Unknown resource: {rid}")
    async with _dl_lock:
        if _dl_state.get(rid, {}).get("status") == "downloading":
            return {"status":"already_downloading"}
    asyncio.create_task(_download_resource(rid))
    return {"status":"started"}

@app.get("/tts/download_progress")
async def download_progress():
    async with _dl_lock:
        return dict(_dl_state)





# Dictionary endpoints
CUSTOM_DICT_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(filename: str) -> list[dict]:
    path = CUSTOM_DICT_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(filename: str, fieldnames: list[str], rows: list[dict]):
    path = CUSTOM_DICT_DIR / filename
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _get_csv_fieldnames(filename: str) -> list[str]:
    if filename == "acronyms.csv":
        return ["acronym", "transliteration"]
    return ["original", "transliteration"]


def _key_col(filename: str) -> str:
    return "acronym" if filename == "acronyms.csv" else "original"


async def _list_dict(filename: str) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _read_csv, filename)


async def _save_dict(filename: str, key: str, value: str) -> list[dict]:
    loop = asyncio.get_running_loop()
    key_col = _key_col(filename)
    val_col = "transliteration"

    def _do():
        rows = _read_csv(filename)
        existing = None
        for r in rows:
            if r.get(key_col, "").strip().lower() == key.strip().lower():
                existing = r
                break
        if existing:
            existing[val_col] = value.strip()
        else:
            rows.append({key_col: key.strip(), val_col: value.strip()})
        _write_csv(filename, _get_csv_fieldnames(filename), rows)
        return rows

    rows = await loop.run_in_executor(None, _do)
    invalidate_normalizer_cache()
    return rows


async def _delete_dict(filename: str, key: str) -> list[dict]:
    loop = asyncio.get_running_loop()
    key_col = _key_col(filename)

    def _do():
        rows = _read_csv(filename)
        rows = [r for r in rows if r.get(key_col, "").strip().lower() != key.strip().lower()]
        _write_csv(filename, _get_csv_fieldnames(filename), rows)
        return rows

    rows = await loop.run_in_executor(None, _do)
    invalidate_normalizer_cache()
    return rows


@app.get("/tts/dict/acronyms")
async def get_acronyms():
    rows = await _list_dict("acronyms.csv")
    return {"entries": [{"key": r["acronym"], "value": r["transliteration"]} for r in rows]}


@app.post("/tts/dict/acronyms")
async def save_acronym(entry: DictEntry):
    rows = await _save_dict("acronyms.csv", entry.key, entry.value)
    return {"entries": [{"key": r["acronym"], "value": r["transliteration"]} for r in rows]}


@app.delete("/tts/dict/acronyms")
async def delete_acronym(key: str = Query(...)):
    rows = await _delete_dict("acronyms.csv", key)
    return {"entries": [{"key": r["acronym"], "value": r["transliteration"]} for r in rows]}


@app.get("/tts/dict/words")
async def get_words():
    rows = await _list_dict("non-vietnamese-words.csv")
    return {"entries": [{"key": r["original"], "value": r["transliteration"]} for r in rows]}


@app.post("/tts/dict/words")
async def save_word(entry: DictEntry):
    rows = await _save_dict("non-vietnamese-words.csv", entry.key, entry.value)
    return {"entries": [{"key": r["original"], "value": r["transliteration"]} for r in rows]}


@app.delete("/tts/dict/words")
async def delete_word(key: str = Query(...)):
    rows = await _delete_dict("non-vietnamese-words.csv", key)
    return {"entries": [{"key": r["original"], "value": r["transliteration"]} for r in rows]}


@app.get("/tts/pause_config")
async def get_pause_config():
    return _load_pause_config()


@app.post("/tts/pause_config")
async def save_pause_config(body: PauseConfigBody):
    _save_pause_config(body.config)
    return _load_pause_config()


# History
HISTORY_FILE = CUSTOM_DICT_DIR / "_history.json"
MAX_HISTORY = 30


async def _save_history(task_id: str):
    task = await task_manager.get(task_id)
    if not task or task.get("status") != "done":
        return
    import time as _time
    entry = {
        "id": task_id, "timestamp": _time.time(),
        "text": task["text"][:200], "voice_mode": task["voice_mode"],
        "voice_id": task["voice_id"], "audio_url": task.get("audio_url", ""),
        "duration": task.get("duration", 0), "output_format": task.get("output_format", "mp3"),
    }
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    history = [h for h in history if h.get("id") != task_id]
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/tts/history")
async def get_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


@app.delete("/tts/history/{history_id}")
async def delete_history(history_id: str):
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    history = [h for h in history if h.get("id") != history_id]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "deleted"}


@app.delete("/tts/history")
async def clear_history():
    HISTORY_FILE.write_text("[]", encoding="utf-8")
    return {"status": "cleared"}


# Serve frontend
# Serve frontend
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    try:
        import uvicorn
        reload_enabled = not getattr(sys, 'frozen', False)
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=reload_enabled)
    except Exception as e:
        import traceback
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        print(f"\nFATAL: {e}\nSee error.log for details.")
        os.system("pause")


# ─── Voice Cloning & Management (CPU) ───

def _normalize_voice_name(name: str) -> str:
    import unicodedata
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())
    return re.sub(r'_+', '_', name).strip('_')

@app.post("/tts/clone")
async def clone_voice(voice_id: str = Form(...), ref_text: str = Form(...), ref_audio: UploadFile = File(...),
                      gender: str = Form("male"), description: str = Form("No description")):
    raw_name = voice_id.strip()
    vid = _normalize_voice_name(raw_name)
    if not vid:
        raise HTTPException(400, "Voice ID is required")
    if not ref_text.strip():
        raise HTTPException(400, "Reference text is required")

    ext = Path(ref_audio.filename).suffix if ref_audio.filename else ".wav"
    vdir = get_voices_dir()
    target_audio = vdir / f"{vid}{ext}"
    content = await ref_audio.read()
    with open(target_audio, "wb") as f:
        f.write(content)

    meta_file = vdir / "voices.json"
    entries = []
    if meta_file.exists():
        try:
            entries = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    entries = [e for e in entries if Path(e.get("audio_path", "")).stem != vid]
    entries.append({
        "name": raw_name,
        "gender": gender,
        "audio_path": f"{vid}{ext}",
        "description": description,
        "text_ref": ref_text,
        "clone": True,
    })
    meta_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"voice_id": vid, "raw_name": raw_name, "status": "cloned"}

@app.delete("/tts/voices/{voice_id}")
async def delete_voice(voice_id: str):
    vdir = get_voices_dir()
    meta_file = vdir / "voices.json"
    if not meta_file.exists():
        raise HTTPException(404, "Voice not found")
    try:
        entries = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        entries = []
    entry = next((e for e in entries if Path(e.get("audio_path", "")).stem == voice_id), None)
    if not entry:
        raise HTTPException(404, "Voice not found")
    for ext in (".wav", ".mp3", ".txt"):
        f = vdir / f"{voice_id}{ext}"
        if f.exists():
            f.unlink()
    entries = [e for e in entries if Path(e.get("audio_path", "")).stem != voice_id]
    meta_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "deleted", "voice_id": voice_id}
