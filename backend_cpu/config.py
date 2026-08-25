import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default))


# Electron sets CAPCAP_DATA_DIR to a writable per-user directory for packaged apps.
APP_DATA_DIR = _env_path("CAPCAP_DATA_DIR", str(PROJECT_ROOT / "backend_cpu"))
CUSTOM_DICT_DIR = APP_DATA_DIR / "custom_dict"
OUTPUT_DIR = APP_DATA_DIR / "outputs"
CUSTOM_DICT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_RESOURCE = PROJECT_ROOT.parent / "TTS_Resource"
PIPER_DIR = _env_path("PIPER_DIR", str(_DEFAULT_RESOURCE / "piper"))
FFMPEG_DIR = _env_path("FFMPEG_DIR", str(PROJECT_ROOT / "ffmpeg" / "bin"))

MAX_TEXT_LENGTH = 5000
PIPER_SAMPLE_RATE = 22050
CROSS_FADE_MS = 50
