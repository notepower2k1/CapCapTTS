# CapCap TTS — Vietnamese Text-to-Speech

<p align="center">
  <b>English</b> | <a href="README.md">Tiếng Việt</a>
</p>

> **100% Free · 100% Local · No API Keys · No Limits**

A lightweight, self-hosted Vietnamese Text-to-Speech desktop app and web service. Runs entirely on your local machine with zero data sent outside.

![CapCap TTS UI](./screenshot.png)

---

## 4 Quality Tiers

| Tier | Engine | Sample Rate | Speed | Quality | Hardware |
|---|---|:---:|:---:|:---:|---|
| **Low** | **Piper** | 22.05 kHz | ⚡⚡⚡ Very Fast | Good | Any CPU |
| **Medium-Low** | **VieNeu-TTS** | **48.0 kHz** | ⚡⚡ Fast | Very Good (Expressive) | CPU or GPU |
| **Medium** | **F5-TTS** | 24.0 kHz | ⚡ Moderate | Excellent (Voice Cloning) | NVIDIA GPU (4GB+) |
| **High** | **OmniVoice** | 24.0 kHz | ⏳ Slower | Best Quality | NVIDIA GPU (6GB+) |

- **Piper**: 25 Vietnamese voices (Northern, Central, Southern).
- **VieNeu**: 20 default voices (10 Male, 10 Female) + Voice Cloning.
- **F5-TTS & OmniVoice**: Shared voice cloning pool with reference audio.

---

## Key Features

- **Vietnamese Normalization**: Auto-converts numbers, dates, currencies, abbreviations (`vietnormalizer`).
- **Resource Manager**: In-app 1-click download, ⚡ **Fast Mirror (`hf-mirror.com`)**, manual download guide, and custom storage folder.
- **Smart Chunking**: Hybrid (default), sentence, or paragraph splitting.
- **Per-Segment Control**: Assign different voices per sentence; regenerate individual segments.
- **Quality Check**: Auto-flags low volume, clipping, excessive silence, or incomplete audio.
- **Batch Processing**: Drag & drop multiple `.txt`/`.md` files with individual or global settings.
- **Export Formats**: Individual WAVs, ZIP bundle, merged MP3 (128k/320k), WAV, and SRT subtitles.
- **Voice Cloning Studio**: Clone new voices from short 3–10s audio clips.
- **Pronunciation Dictionary & Pause Tuning**: Custom acronyms, loanwords, and punctuation pause durations.
- **Bilingual & Dark Mode**: Instant switch between English and Vietnamese.

---

## Hardware Recommendations

| Setup | Mode | Supported Tiers |
|---|---|---|
| **NVIDIA GPU (6GB+ VRAM)** | `backend/` (GPU) | All 4 tiers: Low, Medium-Low, Medium, High |
| **NVIDIA GPU (4GB VRAM)** | `backend/` (GPU) | Low, Medium-Low, Medium |
| **CPU Only / Mac / AMD** | `backend_cpu/` (CPU) | Low (Piper) & Medium-Low (VieNeu ONNX) |

---

## Quick Start

### Prerequisites
- **Python 3.11+** (added to PATH)
- **FFmpeg** (installed and added to PATH or set in `config.py`)

### 1. Desktop App (Electron — Recommended)

```bash
npm install

# Development
npm run start:cpu   # CPU mode (Piper + VieNeu)
npm run start:gpu   # GPU mode (All engines)

# Build Windows Installers (.exe)
npm run build:cpu
npm run build:gpu
```

### 2. Standalone Server Mode

```bash
# GPU Version
cd backend && pip install -r requirements.txt && python main.py

# CPU Version
cd backend_cpu && pip install -r requirements.txt && python main.py
```
Open `http://localhost:8000` in your browser.

---

## Models & Resources

Download directly via **Resources** (`Tài nguyên`) in the app, or fetch manually:

| Model | Size | Source |
|---|:---:|---|
| **Piper Voices** | ~1.5 GB | [Hacht/CapCapResource (piper-new)](https://huggingface.co/Hacht/CapCapResource/tree/main/piper-new) |
| **VieNeu-TTS** | ~330 MB | [pnnbao-ump/VieNeu-TTS-v3-Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo) |
| **Voice References** | ~1.8 MB | [Hacht/CapCapResource (f5_voice)](https://huggingface.co/Hacht/CapCapResource/tree/main/f5_voice) |
| **F5-TTS Model** | ~1.3 GB | [Hacht/CapCapResource (f5_model)](https://huggingface.co/Hacht/CapCapResource/tree/main/f5_model) |
| **OmniVoice Model** | ~2.3 GB | [kjanh/KhanhTTS-OmniVoice](https://huggingface.co/kjanh/KhanhTTS-OmniVoice) |

> ⚡ **Tip**: Enable **"Fast Mirror download (hf-mirror.com)"** in the app if international Hugging Face bandwidth is slow.

---

## Essential API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tts/voices` | List available voices by tier (`low`, `turbo`, `medium`, `high`) |
| `POST` | `/tts/preview` | Generate quick voice preview |
| `POST` | `/tts/generate` | Start speech synthesis task |
| `GET` | `/tts/status/{task_id}` | Check task progress & quality check issues |
| `POST` | `/tts/merge` | Merge segments into MP3/WAV/SRT |
| `POST` | `/tts/regenerate_chunk` | Regenerate a single segment |
| `GET` | `/tts/download_file` | Download generated audio |
| `POST` | `/tts/clone` | Register a new cloned voice |
| `DELETE` | `/tts/voices/{id}` | Delete custom cloned voice |
| `GET/POST` | `/tts/settings` | Get / update storage path and mirror speedup |
| `GET` | `/tts/resource_catalog` | Resource download status & info |
| `POST` | `/tts/download_resource` | Trigger background model download |
| `GET/POST/DELETE` | `/tts/dict/acronyms` | Custom acronym dictionary |
| `GET/POST/DELETE` | `/tts/dict/words` | Custom pronunciation dictionary |

---

## Project Structure

```
TTS/
├── backend/            # GPU backend (FastAPI, PyTorch, F5-TTS, OmniVoice, VieNeu)
├── backend_cpu/        # Lightweight CPU backend (ONNX Runtime, Piper, VieNeu)
├── frontend/           # Web GUI, audio player, i18n localization
├── electron/           # Desktop app main process and launchers
├── electron-builder.base.cjs # Windows installer configuration
└── setup_portable.bat  # Automated portable environment setup
```

---

## License & Credits

- License: [Apache 2.0](./LICENSE)
- Powered by: [VieNeu-TTS](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo), [OmniVoice](https://huggingface.co/kjanh/KhanhTTS-OmniVoice), [F5-TTS](https://github.com/nguyenthienhy/F5-TTS-Vietnamese), [vietnormalizer](https://github.com/nghimestudio/vietnormalizer), [Piper](https://github.com/rhasspy/piper).
