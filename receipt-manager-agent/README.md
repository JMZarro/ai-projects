# Receipt Manager — Standalone Windows Application

A standalone Windows desktop application for autonomous financial receipt scanning, Gemini AI multimodal data extraction, safe spreadsheet recording, and organized file archiving.

This application is the complete standalone implementation of the autonomous workflow specified in [receipt-manager.md](receipt-manager.md) and governed by the learned rules in [GEMINI.md](GEMINI.md).

---

## 🚀 Quick Start

### Option 1: Run the Standalone Windows Executable (.exe)
You can launch the application directly without needing Python installed:
- Navigate to `dist\` and double-click **`ReceiptManager.exe`**.

### Option 2: Run via Python Source
```bash
python main.py
```
Or for headless command-line execution:
```bash
python main.py --cli
```

---

## ✨ Features & Architecture

### 1. Modern Windows Desktop GUI
- Built with **CustomTkinter** featuring smooth dark/light/system theme switching.
- **User Input Text Fields & Smart Autofill (Learned Rule 3)**:
  - On launch, a dedicated window opens displaying text fields for:
    - **Unprocessed Receipts Folder**
    - **Archive Folder**
    - **Master Spreadsheet File**
  - **Initial Execution**: Starts with clean, clear text fields prompting the user to type or browse for their directories.
  - **Subsequent Executions**: Automatically autofills the text fields with the values from previous executions.
  - Changes to paths and credentials are automatically saved when entered or executed, and can also be saved manually with the **"💾 Save Paths"** button.
- **Live Connection & Scan Badges**:
  - Live count of pending receipts ready for processing.
  - "Test Connection" button to verify your Gemini API key immediately.
- **One-Click Shortcuts**:
  - Open Unprocessed Receipts folder directly in Windows Explorer.
  - Open master spreadsheet in Microsoft Excel.
  - Open `Logs.txt` directly in your text editor.
- **Real-Time Color-Coded Activity Log**:
  - Visual output of `[Success]`, `[Warning]`, `[Error]`, and `[Info]` records matching the standard log format.
  - Copy and clear log controls.
- **Batch Summary Modal**:
  - Comprehensive report showing receipts found, processed count, warnings, and failures.

### 2. Autonomous Extraction Engine ([`src/extractor.py`](src/extractor.py))
- Uses Google Gemini multimodal vision capabilities (`gemini-2.5-flash`, `gemini-2.0-flash`, or `gemini-1.5-flash`).
- Automatically handles **PDF receipts** and **all major image formats** (`.png`, `.jpg`, `.jpeg`, `.webp`, and iPhone `.heic` photos via `pillow-heif`).
- Enforces strict Pydantic structured output for:
  - **Business Name (Column A)**: Vendor, restaurant, store, or merchant name.
  - **Category (Column B)**: Strictly assigned from the 13 drop-down categories:
    - `Education`, `Entertainment`, `Gift`, `Groceries`, `Insurance`, `Investment`, `Medical`, `Rent`, `Services`, `Supplies`, `Tax`, `Travel`, `Utilities`.
    - *Disambiguation Rule*: Defaults to `Entertainment` when in doubt (per Learned Rule 2).
  - **Date (Column C)**: Normalized strictly to `MM/DD/YYYY`.
  - **Total Amount (Column D)**: Final numeric grand total.

### 3. Safe Spreadsheet Recording ([`src/excel_handler.py`](src/excel_handler.py))
- Directly updates `.xlsx` (or `.csv`) spreadsheets using `openpyxl`.
- **Zero COM Dependencies**: Avoids Windows Excel COM RPC lockups (`RPC_E_CALL_REJECTED`).
- **Never Overwrites Existing Rows**: Scans from the top and appends records strictly to the next empty row in the `Expenses` sheet.
- **Preserves Formatting & Formulas**: Formats dates (`m/d/yyyy`), currency (`"$"#,##0.00`), and retains existing data validation dropdowns and other sheet formulas (`Balance`, `Total Income`, etc.).
- **Excel Lock Detection**: Alerts you gracefully if the spreadsheet is open in Excel rather than corrupting or failing silently.

### 4. File Archiving & Error Quarantine ([`src/file_manager.py`](src/file_manager.py))
- Successfully processed files are moved from `Unprocessed Receipts` to `Receipts`.
- If a file with an identical name already exists in the archive folder, it automatically appends a numeric suffix (e.g., `receipt_1.pdf`) and logs a `[Warning]`.
- **Critical Error Quarantine**: If an error occurs during extraction, spreadsheet write, or moving, processing is immediately aborted for that file, an `[Error]` is logged, the file remains safely in `Unprocessed Receipts`, and the batch proceeds to the next receipt.

### 5. Strict Logging ([`src/logger.py`](src/logger.py))
- Adheres to **Learned Rule 1**: Logs are written directly to `Logs.txt` in the same directory as the spreadsheet (e.g., `G:\My Drive\Finances\2026\Logs.txt`).
- Follows the exact log format:
  ```log
  YYYY-MM-DD HH:MM:SS [TAG] <Filename>: <Details>
  ```
  Example:
  ```log
  2026-10-14 11:30:15 [Success] receipt_aldi_01.jpg: Recorded "ALDI" | "Groceries" | 05/04/2026 | $42.50 to row 200 in 2026 Finances.xlsx (Expenses). File moved.
  ```

---

## 🛠 Rebuilding the Executable

To compile a new standalone executable after making changes to the source code:
```bash
python build.py
```
The output executable will be created in `dist\ReceiptManager.exe`.
