from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default))

_RESOURCE_DIR = PROJECT_ROOT / "resources"

PIPER_DIR = _env_path("PIPER_DIR", str(_RESOURCE_DIR / "piper"))
OUTPUT_DIR = PROJECT_ROOT / "backend_cpu" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_DIR = _env_path("FFMPEG_DIR", str(PROJECT_ROOT / "ffmpeg" / "bin"))

MAX_TEXT_LENGTH = 5000
PIPER_SAMPLE_RATE = 22050
CROSS_FADE_MS = 50
