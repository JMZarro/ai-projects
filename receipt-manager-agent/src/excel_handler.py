import os
import csv
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import openpyxl

def append_receipt_record(
    spreadsheet_path: Path,
    business_name: str,
    category: str,
    date_str: str, # MM/DD/YYYY
    total_amount: float
) -> Tuple[bool, int, str, Optional[str]]:
    """
    Appends the extracted receipt data to the spreadsheet.
    Returns (success, row_number, sheet_or_file_name, error_message).
    """
    if not spreadsheet_path.exists():
        return False, 0, "", f"Spreadsheet file not found: {spreadsheet_path}"

    ext = spreadsheet_path.suffix.lower()

    if ext == ".xlsx":
        try:
            wb = openpyxl.load_workbook(str(spreadsheet_path), data_only=False)
        except PermissionError:
            return False, 0, "", f"Cannot open '{spreadsheet_path.name}'. File is currently locked or open in Excel. Please close it and retry."
        except Exception as e:
            return False, 0, "", f"Failed to load Excel workbook: {str(e)}"

        try:
            # Look for 'Expenses' sheet or default to active
            target_sheet_name = None
            for name in wb.sheetnames:
                if name.strip().lower() == "expenses":
                    target_sheet_name = name
                    break
            
            if target_sheet_name:
                ws = wb[target_sheet_name]
            else:
                ws = wb.active
                target_sheet_name = ws.title

            # Locate next available empty row (where Col 1 is empty or None)
            target_row = None
            # Scan from row 2 up to max_row + 100
            scan_limit = max(ws.max_row + 10, 500)
            for r in range(2, scan_limit):
                val_a = ws.cell(r, 1).value
                val_b = ws.cell(r, 2).value
                val_c = ws.cell(r, 3).value
                val_d = ws.cell(r, 4).value
                
                # Check if entire record part of row is empty
                is_empty = (
                    (val_a is None or str(val_a).strip() == "") and
                    (val_b is None or str(val_b).strip() == "") and
                    (val_c is None or str(val_c).strip() == "") and
                    (val_d is None or str(val_d).strip() == "")
                )
                if is_empty:
                    target_row = r
                    break

            if target_row is None:
                target_row = ws.max_row + 1

            # Parse date_str into datetime.date object
            dt_obj = datetime.strptime(date_str, "%m/%d/%Y").date()

            # Set Column Values
            ws.cell(target_row, 1, value=business_name)
            ws.cell(target_row, 2, value=category)
            
            # Date in Col 3
            cell_date = ws.cell(target_row, 3, value=dt_obj)
            cell_date.number_format = 'm/d/yyyy'

            # Total Amount in Col 4
            cell_amt = ws.cell(target_row, 4, value=float(total_amount))
            cell_amt.number_format = '"$"#,##0.00'

            # Save workbook
            wb.save(str(spreadsheet_path))
            wb.close()

            return True, target_row, target_sheet_name, None

        except PermissionError:
            return False, 0, "", f"Failed to save changes. '{spreadsheet_path.name}' is open in Excel or another program. Close it and retry."
        except Exception as e:
            return False, 0, "", f"Failed to write row to Excel: {str(e)}"

    elif ext == ".csv":
        try:
            row_count = 0
            with open(spreadsheet_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                for _ in reader:
                    row_count += 1

            target_row = row_count + 1
            with open(spreadsheet_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([business_name, category, date_str, f"{total_amount:.2f}"])

            return True, target_row, spreadsheet_path.name, None
        except PermissionError:
            return False, 0, "", f"Cannot save to CSV '{spreadsheet_path.name}'. File is open in another program."
        except Exception as e:
            return False, 0, "", f"Failed to write to CSV: {str(e)}"

    else:
        return False, 0, "", f"Unsupported spreadsheet file extension: '{ext}'. Must be .xlsx or .csv."
