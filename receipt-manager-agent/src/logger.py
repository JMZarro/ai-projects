import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

class ReceiptLogger:
    def __init__(self, spreadsheet_path: str, ui_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initializes logger for receipt operations.
        Logs are written to 'Logs.txt' located in the SAME folder path as spreadsheet_path.
        """
        self.spreadsheet_path = Path(spreadsheet_path) if spreadsheet_path else None
        self.ui_callback = ui_callback
        self.log_file_path: Optional[Path] = None

        if self.spreadsheet_path and self.spreadsheet_path.parent.exists():
            self.log_file_path = self.spreadsheet_path.parent / "Logs.txt"

    def set_spreadsheet_path(self, spreadsheet_path: str):
        self.spreadsheet_path = Path(spreadsheet_path) if spreadsheet_path else None
        if self.spreadsheet_path and self.spreadsheet_path.parent.exists():
            self.log_file_path = self.spreadsheet_path.parent / "Logs.txt"
        else:
            self.log_file_path = None

    def _write_log(self, tag: str, message: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{now_str} [{tag}] {message}\n"

        if self.log_file_path:
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(log_line)
            except Exception as e:
                print(f"Error writing to {self.log_file_path}: {e}")

        if self.ui_callback:
            try:
                self.ui_callback(tag, log_line.strip())
            except Exception:
                pass

    def success(self, filename: str, details: str):
        self._write_log("Success", f"{filename}: {details}")

    def warning(self, filename: str, details: str):
        self._write_log("Warning", f"{filename}: {details}")

    def error(self, filename: str, details: str):
        self._write_log("Error", f"{filename}: {details}")

    def info(self, message: str):
        self._write_log("Info", message)
