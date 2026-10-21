import os
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple

from .config import load_config
from .logger import ReceiptLogger
from .file_manager import get_unprocessed_files, move_to_processed
from .extractor import extract_receipt_data
from .excel_handler import append_receipt_record

class ReceiptProcessor:
    def __init__(
        self,
        unprocessed_folder: str,
        processed_folder: str,
        spreadsheet_path: str,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        logger: Optional[ReceiptLogger] = None,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ):
        self.unprocessed_folder = Path(unprocessed_folder) if unprocessed_folder else Path("")
        self.processed_folder = Path(processed_folder) if processed_folder else Path("")
        self.spreadsheet_path = Path(spreadsheet_path) if spreadsheet_path else Path("")
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logger or ReceiptLogger(spreadsheet_path)
        self.progress_callback = progress_callback
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def validate_environment(self) -> Tuple[bool, str]:
        """Performs pre-flight checks on paths and credentials."""
        if not self.api_key:
            return False, "Gemini API Key is missing. Please configure your API key in Settings."

        if not self.unprocessed_folder.exists() or not self.unprocessed_folder.is_dir():
            return False, f"Unprocessed Receipts folder does not exist: {self.unprocessed_folder}"

        if not self.processed_folder.exists():
            try:
                self.processed_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Processed folder does not exist and could not be created: {e}"

        if not self.spreadsheet_path.exists() or not self.spreadsheet_path.is_file():
            return False, f"Spreadsheet file does not exist: {self.spreadsheet_path}"

        # Test write permission on spreadsheet
        try:
            with open(self.spreadsheet_path, "a+b"):
                pass
        except PermissionError:
            return False, (
                f"The spreadsheet '{self.spreadsheet_path.name}' is currently locked. "
                "If it is open in Microsoft Excel or another program, please close it and try again."
            )
        except Exception as e:
            return False, f"Cannot access spreadsheet for writing: {e}"

        return True, "Environment verified successfully."

    def run(self) -> Dict[str, Any]:
        """
        Executes the receipt processing batch.
        Returns a summary report dictionary.
        """
        self.is_cancelled = False
        summary = {
            "total_found": 0,
            "success_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "failures": [],
            "status": "Completed"
        }

        # Step 1: Pre-flight checks
        valid, msg = self.validate_environment()
        if not valid:
            summary["status"] = f"Aborted: {msg}"
            self.logger.error("Pre-Flight Check", msg)
            return summary

        # Scan for pending files
        files = get_unprocessed_files(self.unprocessed_folder)
        summary["total_found"] = len(files)

        if len(files) == 0:
            info_msg = "Scan completed: 0 pending receipts found to process."
            self.logger.info(info_msg)
            summary["status"] = info_msg
            if self.progress_callback:
                self.progress_callback(0, 0, "", info_msg)
            return summary

        # Step 2: Per-file processing loop
        total = len(files)
        for idx, file_path in enumerate(files, start=1):
            if self.is_cancelled:
                self.logger.info("Batch processing cancelled by user.")
                summary["status"] = "Cancelled by user"
                break

            filename = file_path.name
            if self.progress_callback:
                self.progress_callback(idx, total, filename, f"Processing {idx} of {total}: {filename}...")

            # 1. Extraction
            extraction, extract_err = extract_receipt_data(
                file_path=file_path,
                api_key=self.api_key,
                model_name=self.model_name
            )

            if extract_err or not extraction:
                error_msg = f"{extract_err or 'Failed to extract required fields'}. Aborted."
                self.logger.error(filename, error_msg)
                summary["error_count"] += 1
                summary["failures"].append({"filename": filename, "reason": error_msg})
                # Critical Rule: Abort this receipt, leave file in unprocessed, proceed to next
                continue

            # 2. Record to spreadsheet
            success, row_num, sheet_name, write_err = append_receipt_record(
                spreadsheet_path=self.spreadsheet_path,
                business_name=extraction.business_name,
                category=extraction.category,
                date_str=extraction.date,
                total_amount=extraction.total_amount
            )

            if not success:
                error_msg = f"Failed to record to spreadsheet: {write_err}. Aborted."
                self.logger.error(filename, error_msg)
                summary["error_count"] += 1
                summary["failures"].append({"filename": filename, "reason": error_msg})
                continue

            # 3. Move receipt file
            try:
                dest_path, was_renamed = move_to_processed(file_path, self.processed_folder)
                if was_renamed:
                    self.logger.warning(
                        filename,
                        f"Destination file existed; moved as {dest_path.name}."
                    )
                    summary["warning_count"] += 1
            except Exception as e:
                move_err = f"Failed to move file to processed folder: {str(e)}. Aborted."
                self.logger.error(filename, move_err)
                summary["error_count"] += 1
                summary["failures"].append({"filename": filename, "reason": move_err})
                continue

            # 4. Success Log
            success_details = (
                f'Recorded "{extraction.business_name}" | "{extraction.category}" | '
                f'{extraction.date} | ${extraction.total_amount:.2f} to row {row_num} in '
                f'{self.spreadsheet_path.name} ({sheet_name}). File moved.'
            )
            self.logger.success(filename, success_details)
            summary["success_count"] += 1

        if self.progress_callback:
            self.progress_callback(
                total,
                total,
                "",
                f"Batch finished. {summary['success_count']} succeeded, {summary['error_count']} failed."
            )

        return summary
