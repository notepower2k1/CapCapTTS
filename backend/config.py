import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default))

_RESOURCE_DIR = PROJECT_ROOT / "resources"

F5_RESOURCE_DIR = _env_path("F5_RESOURCE_DIR", str(_RESOURCE_DIR / "f5"))
F5_MODEL_DIR = F5_RESOURCE_DIR
F5_VOICES_DIR = F5_RESOURCE_DIR / "f5_voice"
F5_VOCODER_DIR = F5_RESOURCE_DIR / "checkpoints" / "vocos-mel-24khz"

OMNIVOICE_VOICES_DIR = F5_VOICES_DIR
OMNIVOICE_MODEL_DIR = F5_RESOURCE_DIR / "omnivoice"

PIPER_DIR = _env_path("PIPER_DIR", str(_RESOURCE_DIR / "piper"))

FFMPEG_DIR = _env_path("FFMPEG_DIR", str(PROJECT_ROOT / "ffmpeg" / "bin"))

OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_TEXT_LENGTH = 5000
PIPER_SAMPLE_RATE = 22050
F5_SAMPLE_RATE = 24000
CROSS_FADE_MS = 50
