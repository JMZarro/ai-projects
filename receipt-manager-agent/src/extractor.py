import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal, Tuple
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from .config import CATEGORIES, DEFAULT_CATEGORY
from .file_manager import prepare_file_for_api

CategoryType = Literal[
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

class ReceiptSchema(BaseModel):
    business_name: str = Field(description="The name of the merchant, store, restaurant, or service provider.")
    category: CategoryType = Field(
        description="Categorization of purchase strictly from the allowed options. Default to Entertainment when in doubt."
    )
    date: str = Field(description="Transaction date formatted strictly as MM/DD/YYYY.")
    total_amount: float = Field(description="The final grand total charged including taxes and fees as a decimal number.")
    confidence: bool = Field(description="True if business name, date, and total amount were identified with high confidence, False otherwise.")
    error_reason: Optional[str] = Field(default=None, description="Explanation if confidence is False or extraction is incomplete.")

SYSTEM_INSTRUCTION = """You are an expert autonomous financial receipt processing agent.
Your objective is to inspect receipt images or PDFs and accurately extract the transaction data.

Follow these strict rules:
1. Business Name (Column A): Merchant, vendor, store, restaurant, or service provider (e.g., "ALDI", "Lidl", "The Leafy Basket", "Target", "Burlington", "Village Liquors").
2. Category (Column B): Choose strictly from one of the following 13 categories:
   - Education: Learning, classes, certifications, exams.
   - Entertainment: Purely for joy or recreation (e.g. eating at restaurants, coffee shops, bakeries, bars, games, hotels).
     * Disambiguation: Check all other categories first. When in doubt or unknown, choose 'Entertainment'.
   - Gift: Purchases specifically made for someone else (gift wrapping/cards). If unknown, categorize as 'Entertainment'.
   - Groceries: Food items requiring cooking; any grocery store or supermarket (e.g. Lidl, Aldi, The Leafy Basket, ShopRite, Stop & Shop, Acme, Seabra).
   - Insurance: Payments to insurance companies (car, health, life, home).
   - Investment: Stock purchases, retirement accounts, IRA transfers.
   - Medical: Doctors, pharmacies, copays, deductibles, prescriptions not covered by insurance.
   - Rent: Living/apartment/house rent.
   - Services: Bills for home contractors, plumbers, electricians, landscapers.
   - Supplies: Human non-food personal items (shampoo, clothes), home improvement/hardware (Lowe's, Home Depot, Burlington, Target, Amazon), and ANYTHING bought for pets (pet food, pet toys, PetSmart).
   - Tax: Government tax payments.
   - Travel: Transportation and vehicle fuel (gas stations like Fuel 4, Sunoco, BP; rental cars, trains, flights, MTA, NJT).
   - Utilities: Household utilities (electricity, water, gas, internet, PSE&G, Xfinity).
3. Date (Column C): Strictly formatted as MM/DD/YYYY (e.g., 08/24/2026).
4. Total Amount (Column D): Final grand total charged (including taxes and fees) as a numeric decimal.

If Business Name, Date, or Total Amount cannot be determined with confidence, set confidence=False and state the reason in error_reason.
"""

EXTRACTION_PROMPT = """Analyze this receipt document carefully.
Extract the merchant/business name, category, transaction date (MM/DD/YYYY), and final total amount.
Return the structured data matching the schema.
"""

def parse_normalized_date(date_str: str) -> Optional[datetime]:
    """Attempts multiple date formats and returns a valid datetime object."""
    date_str = date_str.strip()
    formats = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%m/%d/%y", "%m-%d-%y", "%B %d, %Y", "%b %d, %Y",
        "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try regex match for M/D/YYYY or MM/DD/YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", date_str)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day)
        except ValueError:
            pass
    return None

def extract_receipt_data(
    file_path: Path,
    api_key: str,
    model_name: str = "gemini-2.5-flash"
) -> Tuple[Optional[ReceiptSchema], Optional[str]]:
    """
    Extracts transaction fields from a receipt file using Gemini API.
    Returns (ReceiptSchema, None) on success or (None, error_message) on failure.
    """
    if not api_key:
        return None, "Gemini API key is not configured."

    prepared_path, is_temp = prepare_file_for_api(file_path)
    client = genai.Client(api_key=api_key)
    file_ref = None

    try:
        # Determine mime type
        ext = prepared_path.suffix.lower()
        mime_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"

        # Upload file to Gemini Files API
        file_ref = client.files.upload(
            file=str(prepared_path),
            mime_type=mime_type
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[file_ref, EXTRACTION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReceiptSchema,
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.0,
            )
        )

        if not response.text:
            return None, "Empty response received from Gemini API."

        # Parse result
        data = json.loads(response.text)
        result = ReceiptSchema.model_validate(data)

        # Validate confidence
        if not result.confidence:
            reason = result.error_reason or "Low confidence in extracted fields."
            return None, f"Extraction failed confidence check: {reason}"

        # Clean business name
        result.business_name = result.business_name.strip()
        if not result.business_name:
            return None, "Failed to extract Business Name."

        # Validate and normalize category
        if result.category not in CATEGORIES:
            result.category = DEFAULT_CATEGORY

        # Validate date
        parsed_dt = parse_normalized_date(result.date)
        if not parsed_dt:
            return None, f"Failed to parse valid transaction date from '{result.date}'."
        result.date = parsed_dt.strftime("%m/%d/%Y")

        # Validate amount
        if result.total_amount <= 0.0:
            return None, f"Invalid total amount extracted: {result.total_amount}."

        return result, None

    except Exception as e:
        return None, f"API Error: {str(e)}"

    finally:
        # Cleanup uploaded file from Gemini storage
        if file_ref:
            try:
                client.files.delete(name=file_ref.name)
            except Exception:
                pass
        # Cleanup local temporary converted file if any
        if is_temp and prepared_path.exists():
            try:
                os.remove(str(prepared_path))
            except Exception:
                pass
