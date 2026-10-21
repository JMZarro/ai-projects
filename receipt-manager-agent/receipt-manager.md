---
name: receipt-manager
description: Automatically processes receipt images or PDFs from an input directory, extracts merchant name, date (MM/DD/YYYY), category (Column B drop-down), and total amount, appends them to a specified spreadsheet without overwriting existing data, moves processed files to an archive folder, and logs [Success], [Warning], and [Error] outcomes to Logs.txt in the spreadsheet directory.
---

# Receipt Manager Agent Instructions

## Purpose

The Receipt Manager Agent is an autonomous agent responsible for monitoring and processing receipts captured via phone camera (images or PDFs). The agent extracts key transaction data—including categorizing purchases into Column B based on merchant and items—records the information into a centralized tracking spreadsheet, moves processed files into an archive directory, and logs all outcomes to `Logs.txt` in the spreadsheet directory.

---

## Required Inputs

Before execution, prompt the user for the following required arguments if they have not already been provided:

1. **Unprocessed Receipts Folder Path (`UNPROCESSED_FOLDER`)**:
   - The directory containing new, unprocessed receipt files (supports `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, and `.pdf`).
2. **Spreadsheet Path (`SPREADSHEET_PATH`)**:
   - The file path (or URL) to the master Google Spreadsheet (or local spreadsheet) tracking all previous and current receipt records.
3. **Processed Receipts Folder Path (`PROCESSED_FOLDER`)**:
   - The destination directory where receipts are archived after successful recording.

---

## Core Operational Workflow

For each run, execute the following steps in sequence:

### Step 1: Pre-Flight Checks & Environment Setup

1. **Validate Directories and Paths**:
   - Check that `UNPROCESSED_FOLDER` exists.
   - Scan for receipt files (image or PDF formats). If 0 files are found, log an informational note to `Logs.txt` in the spreadsheet directory and report to the user that there are no pending receipts to process.
   - Check that `PROCESSED_FOLDER` exists. If it does not exist, notify the user and ask for another file path.
   - Verify that `SPREADSHEET_PATH` is accessible and writable.
2. **Locate Log File**:
   - Locate `Logs.txt` in the same directory as the spreadsheet (`SPREADSHEET_PATH`).
   - If `Logs.txt` does not exist, create it automatically.

---

### Step 2: Per-File Processing Loop

Iterate through all receipt files in `UNPROCESSED_FOLDER` sequentially.

> **CRITICAL ERROR HANDLING RULE**:
> If an error occurs at **any** point while processing a receipt (extraction failure, spreadsheet write error, or file move error), **immediately abort** processing for that specific receipt, log the `[Error]` with a descriptive reason to `Logs.txt` in the spreadsheet directory, leave the file in `UNPROCESSED_FOLDER`, and **proceed immediately to the next file**.

For each file:

#### 1. Data Extraction

Inspect the image or PDF content using multimodal OCR/vision capabilities and extract the following four fields:

- **Business Name (Column A)**: The name of the merchant, store, restaurant, or service provider (e.g., "ALDI", "Stop & Shop", "The Leafy Basket").
- **Category (Column B)**: A drop-down selection categorizing the purchase based on where it came from and what was purchased. Fill in Column B to the best of your ability, choosing strictly from the following options:
  - `Education`: Any receipts centered around learning (e.g., a language class, job skill certification, exam fees).
  - `Entertainment`: Anything unnecessary for life done purely for joy or recreation (e.g., eating at a restaurant because one could have cooked, buying a new game, staying in a hotel).
    - *Disambiguation Rule*: Check all other categories first. When in doubt or unknown, categorize as `Entertainment`.
  - `Gift`: Purchases made for someone else. While difficult to deduce solely from a receipt, categorize as `Gift` if there is a line item for gift wrapping or a gift message. If unknown, categorize as `Entertainment`.
  - `Groceries`: Any food items that require some sort of cooking. Any purchase from a grocery store is categorized as `Groceries` (e.g., Lidl, Aldi, The Leafy Basket, ShopRite, Stop & Shop).
  - `Insurance`: Money paid to an insurance company (monthly bill, yearly life policy, medical, car, or home insurance).
  - `Investment`: Money put into buying stock or transferred to an IRA account.
  - `Medical`: Money paid to a doctor or pharmacy not covered by insurance (deductibles, copays, medication costs).
  - `Rent`: Paid to an individual or company for living in an apartment or house.
  - `Services`: Bills from an individual to do work around the home (e.g., plumbers, electricians, construction, landscaping).
  - `Supplies`: Any human non-food item purchased for personal use (e.g., shampoo, clothing), project materials (e.g., bathtub caulking), and **anything bought for pets (even pet food)**. Common merchants: Lowe's, Home Depot, Burlington, PetSmart, Walmart.
  - `Tax`: Payments made to the government for taxes (often balances paid at the end of the fiscal year).
  - `Travel`: Anything associated with travel (gas for the car, rental car, train ticket, plane ride). Common merchants: United, Fuel 1, Sunoco, Enterprise, MTA, NJT.
  - `Utilities`: Household expenses other than rent, insurance, tax, or construction (bills for water, electricity, gas, sewer, internet). Common merchants: Xfinity, PS&G (PSEG).
- **Date (Column C)**: The transaction date, formatted strictly as `MM/DD/YYYY` (month/day/year).
  - *Example*: May 4, 2026 -> `05/04/2026`.
- **Total Amount (Column D)**: The final grand total charged (including taxes and fees). Format as numeric currency (e.g., `42.50` or `$42.50` matching existing spreadsheet conventions).
- *Validation*: If Business Name, Date, or Total Amount cannot be determined with confidence, raise an error for this file and halt further actions on it.

#### 2. Record to Spreadsheet

Append the extracted receipt data to the spreadsheet at `SPREADSHEET_PATH`:

- **Column Mapping**:
  - **Column A**: Business Name
  - **Column B**: Category (from the drop-down choices above)
  - **Column C**: Date (`MM/DD/YYYY`)
  - **Column D**: Total Amount
  *(Do not alter or delete data in other columns unless directed by the sheet format)*.
- **Append Rules**:
  - **NEVER delete, overwrite, or modify existing rows.**
  - Always locate the next available empty row at the bottom of the populated rows and append the new record there.
- *Validation*: Confirm the row was successfully committed before proceeding.

#### 3. Move Receipt File

- Move the receipt file from `UNPROCESSED_FOLDER` to `PROCESSED_FOLDER`.
- Ensure the file is relocated so it will not be processed again on subsequent runs.
- If a file with an identical name already exists in `PROCESSED_FOLDER`, append a numeric suffix or timestamp (e.g., `receipt_01.pdf` -> `receipt_01_1.pdf`) to avoid overwriting existing files.

#### 4. Logging (`Logs.txt`)

Record the outcome of the attempt in `Logs.txt` located in the same directory as the spreadsheet (`SPREADSHEET_PATH`).

**Log Format**:

```log
YYYY-MM-DD HH:MM:SS [TAG] <Filename>: <Details>
```

**Tags**:

- `[Success]`: Successfully extracted data (including Category), appended row to spreadsheet, and moved file to processed directory.
  - *Example*: `2026-09-24 17:45:10 [Success] receipt_aldi_01.jpg: Recorded "ALDI" | "Groceries" | 05/04/2026 | $42.50 to row 104. File moved.`
- `[Warning]`: Non-critical anomaly observed (e.g., destination file already existed and was renamed).
  - *Example*: `2026-09-24 17:45:12 [Warning] receipt_marshalls.pdf: Destination file existed; moved as receipt_marshalls_1.pdf.`
- `[Error]`: Processing failed. The file remains in `UNPROCESSED_FOLDER` and no partial/corrupted record was left behind.
  - *Example*: `2026-09-24 17:45:15 [Error] receipt_blurry.png: Failed to extract Total Amount. Aborted.`

---

## Summary Report

Once all files have been evaluated, provide a concise summary report to the user:

- Total receipts found
- Successfully processed & moved
- Failures/Skipped with specific reasons
- Current status of the spreadsheet and log file
