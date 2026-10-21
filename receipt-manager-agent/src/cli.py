import argparse
import sys
from pathlib import Path

from .config import load_config
from .logger import ReceiptLogger
from .processor import ReceiptProcessor

def run_cli():
    config = load_config()

    parser = argparse.ArgumentParser(
        description="Receipt Manager — Autonomous Multimodal Receipt Processor"
    )
    parser.add_argument(
        "--unprocessed",
        default=config.get("unprocessed_folder", ""),
        help="Path to Unprocessed Receipts folder"
    )
    parser.add_argument(
        "--processed",
        default=config.get("processed_folder", ""),
        help="Path to Processed Archive folder"
    )
    parser.add_argument(
        "--spreadsheet",
        default=config.get("spreadsheet_path", ""),
        help="Path to master spreadsheet (.xlsx or .csv)"
    )
    parser.add_argument(
        "--api-key",
        default=config.get("gemini_api_key", ""),
        help="Google Gemini API Key"
    )
    parser.add_argument(
        "--model",
        default=config.get("model", "gemini-2.5-flash"),
        help="Gemini Model to use"
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: Gemini API key is required. Specify with --api-key or configure in GUI.")
        sys.exit(1)

    if not args.unprocessed or not Path(args.unprocessed).exists():
        print(f"Error: Unprocessed folder does not exist: {args.unprocessed}")
        sys.exit(1)

    if not args.spreadsheet or not Path(args.spreadsheet).exists():
        print(f"Error: Spreadsheet does not exist: {args.spreadsheet}")
        sys.exit(1)

    def print_log(tag: str, line: str):
        print(line)

    logger = ReceiptLogger(args.spreadsheet, ui_callback=print_log)
    processor = ReceiptProcessor(
        unprocessed_folder=args.unprocessed,
        processed_folder=args.processed,
        spreadsheet_path=args.spreadsheet,
        api_key=args.api_key,
        model_name=args.model,
        logger=logger,
        progress_callback=lambda cur, tot, fn, txt: print(f"[{cur}/{tot}] {txt}")
    )

    summary = processor.run()
    print("\n--- Execution Summary ---")
    print(f"Status: {summary['status']}")
    print(f"Total Found: {summary['total_found']}")
    print(f"Successes: {summary['success_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"Warnings: {summary['warning_count']}")
    if summary["failures"]:
        print("Failures:")
        for f in summary["failures"]:
            print(f" - {f['filename']}: {f['reason']}")

if __name__ == "__main__":
    run_cli()
