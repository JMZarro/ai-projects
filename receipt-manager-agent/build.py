import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    root_dir = Path(__file__).parent.resolve()
    main_script = root_dir / "main.py"
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "ReceiptManager",
        "--clean",
        "--collect-all", "customtkinter",
        "--collect-all", "google.genai",
        "--collect-all", "openpyxl",
        "--collect-all", "pillow_heif",
        "--add-data", f"{root_dir / 'src'};src",
        str(main_script)
    ]

    print("Building standalone executable...")
    print("Command:", " ".join(cmd))
    
    result = subprocess.run(cmd, cwd=str(root_dir))
    if result.returncode == 0:
        exe_path = root_dir / "dist" / "ReceiptManager.exe"
        print(f"\n[SUCCESS] Standalone Windows executable built successfully at:\n{exe_path}")
    else:
        print(f"\n[ERROR] Build failed with return code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build_executable()
