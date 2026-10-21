import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf"}

def get_unprocessed_files(unprocessed_dir: Path) -> List[Path]:
    """Scans directory for receipt files matching supported extensions."""
    if not unprocessed_dir.exists() or not unprocessed_dir.is_dir():
        return []
    
    files = []
    for item in unprocessed_dir.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(item)
    
    # Sort files chronologically or alphabetically
    return sorted(files, key=lambda p: p.name.lower())

def prepare_file_for_api(file_path: Path) -> Tuple[Path, bool]:
    """
    If the file is a HEIC image, converts it to a temporary JPEG for Gemini API ingestion.
    Returns (path_to_send, is_temporary).
    """
    ext = file_path.suffix.lower()
    if ext == ".heic":
        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        with Image.open(file_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(temp_path, "JPEG", quality=95)
        return temp_path, True
    
    return file_path, False

def move_to_processed(source_path: Path, processed_dir: Path) -> Tuple[Path, bool]:
    """
    Moves source_path to processed_dir.
    If a file with the identical name already exists in processed_dir,
    appends a numeric suffix (e.g., receipt_1.pdf) to avoid overwriting.
    Returns (final_destination_path, was_renamed).
    """
    if not processed_dir.exists():
        processed_dir.mkdir(parents=True, exist_ok=True)

    dest_path = processed_dir / source_path.name
    was_renamed = False

    if dest_path.exists():
        was_renamed = True
        stem = source_path.stem
        suffix = source_path.suffix
        counter = 1
        while True:
            candidate = processed_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                dest_path = candidate
                break
            counter += 1

    shutil.move(str(source_path), str(dest_path))
    return dest_path, was_renamed
