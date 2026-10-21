import os
import json
from pathlib import Path
from typing import Dict, Any

CATEGORIES = [
    "Education",
    "Entertainment",
    "Gift",
    "Groceries",
    "Insurance",
    "Investment",
    "Medical",
    "Rent",
    "Services",
    "Supplies",
    "Tax",
    "Travel",
    "Utilities"
]

DEFAULT_CATEGORY = "Entertainment"

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def get_config_dir() -> Path:
    """Returns the application configuration directory in %APPDATA%."""
    app_data = os.getenv("APPDATA")
    if app_data:
        cfg_dir = Path(app_data) / "ReceiptManager"
    else:
        cfg_dir = Path.home() / ".receipt_manager"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir

def get_config_path() -> Path:
    return get_config_dir() / "config.json"

def get_default_config() -> Dict[str, Any]:
    # Default paths start blank on initial execution; subsequent runs load autofilled values from config.json
    default_unprocessed = ""
    default_processed = ""
    default_sheet = ""

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

    # Also check ~/.env or local .env
    if not api_key:
        for env_path in [Path.home() / ".env", Path(".env")]:
            if env_path.exists():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY="):
                                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                            elif line.startswith("GOOGLE_API_KEY="):
                                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass

    return {
        "gemini_api_key": api_key,
        "unprocessed_folder": default_unprocessed,
        "processed_folder": default_processed,
        "spreadsheet_path": default_sheet,
        "model": "gemini-2.5-flash",
        "theme": "System"
    }

def load_config() -> Dict[str, Any]:
    cfg = get_default_config()
    cfg_file = get_config_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    return cfg

def save_config(cfg: Dict[str, Any]) -> None:
    cfg_file = get_config_path()
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
