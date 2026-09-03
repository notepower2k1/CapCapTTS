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

import json

SETTINGS_FILE = APP_DATA_DIR / "settings.json"

def get_default_resource_dir() -> Path:
    return Path(os.environ.get("TTS_RESOURCE_DIR", str(PROJECT_ROOT.parent / "TTS_Resource")))

def get_resource_dir() -> Path:
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if "resource_dir" in cfg and cfg["resource_dir"].strip():
                p = Path(cfg["resource_dir"].strip())
                p.mkdir(parents=True, exist_ok=True)
                return p
        except Exception:
            pass
    p = get_default_resource_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p

def set_resource_dir(new_path: str) -> Path:
    p = Path(new_path.strip()) if new_path.strip() else get_default_resource_dir()
    p.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg["resource_dir"] = str(p)
    SETTINGS_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_RESOURCE = PROJECT_ROOT.parent / "TTS_Resource"
PIPER_DIR = _env_path("PIPER_DIR", str(_DEFAULT_RESOURCE / "piper"))
FFMPEG_DIR = _env_path("FFMPEG_DIR", str(PROJECT_ROOT / "ffmpeg" / "bin"))

MAX_TEXT_LENGTH = 5000
PIPER_SAMPLE_RATE = 22050
CROSS_FADE_MS = 50


def get_voices_dir() -> Path:
    p = get_resource_dir() / "f5" / "f5_voice"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_use_mirror() -> bool:
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return bool(cfg.get("use_mirror", False))
        except Exception:
            pass
    return False

def set_use_mirror(val: bool) -> bool:
    cfg = {}
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg["use_mirror"] = bool(val)
    SETTINGS_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    if val:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    else:
        os.environ.pop("HF_ENDPOINT", None)
    return bool(val)



def setup_hf_env():
    hf_dir = get_resource_dir() / "huggingface"
    hf_hub = hf_dir / "hub"
    hf_hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf_dir)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_hub)
    if get_use_mirror():
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    else:
        os.environ.pop("HF_ENDPOINT", None)

setup_hf_env()
