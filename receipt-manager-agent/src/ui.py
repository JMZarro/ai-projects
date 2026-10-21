import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from .config import (
    load_config,
    save_config,
    AVAILABLE_MODELS,
    CATEGORIES
)
from .logger import ReceiptLogger
from .processor import ReceiptProcessor
from .file_manager import get_unprocessed_files

class ReceiptManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load persisted configuration (contains values from previous executions)
        self.config = load_config()

        # Appearance configuration
        self.current_theme = self.config.get("theme", "System")
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        # Window settings
        self.title("Receipt Manager — Autonomous Financial Processing")
        self.geometry("980x830")
        self.minsize(880, 700)

        # State variables
        self.processor: Optional[ReceiptProcessor] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Build UI layout
        self._create_widgets()
        # Populate text fields (autofill previous values if available)
        self._populate_fields()

        # Initial scan update
        self.after(300, self._quick_scan_badge)

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Log area expands

        # ----------------- HEADER FRAME -----------------
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            self.header_frame,
            text="🧾 Receipt Manager",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=16, pady=(10, 2), sticky="w")

        subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Autonomous receipt scanning, Gemini AI extraction & Excel tracking",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray"
        )
        subtitle_label.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        # Theme selector in header
        theme_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        theme_frame.grid(row=0, column=2, rowspan=2, padx=16, pady=8, sticky="e")

        theme_lbl = ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=11))
        theme_lbl.pack(side="left", padx=4)

        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["System", "Dark", "Light"],
            command=self._change_theme,
            width=90,
            height=26,
            font=ctk.CTkFont(size=11)
        )
        self.theme_menu.set(self.current_theme)
        self.theme_menu.pack(side="left")

        # ----------------- DIRECTORIES & SPREADSHEET CARD (USER INPUTS) -----------------
        self.paths_card = ctk.CTkFrame(self, corner_radius=10)
        self.paths_card.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        self.paths_card.grid_columnconfigure(1, weight=1)

        paths_title = ctk.CTkLabel(
            self.paths_card,
            text="Required Inputs — Folders & Master Spreadsheet",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        paths_title.grid(row=0, column=0, columnspan=3, padx=14, pady=(8, 4), sticky="w")

        # 1. Unprocessed Folder Field
        unproc_lbl = ctk.CTkLabel(self.paths_card, text="Unprocessed Receipts:", font=ctk.CTkFont(weight="bold"))
        unproc_lbl.grid(row=1, column=0, padx=14, pady=4, sticky="w")

        self.unproc_entry = ctk.CTkEntry(
            self.paths_card,
            height=32,
            placeholder_text="Enter or browse path to Unprocessed Receipts folder..."
        )
        self.unproc_entry.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.unproc_entry.bind("<FocusOut>", self._on_field_change)
        self.unproc_entry.bind("<KeyRelease>", self._on_field_change)

        unproc_btn = ctk.CTkButton(
            self.paths_card,
            text="Browse...",
            width=80,
            height=32,
            command=self._browse_unprocessed
        )
        unproc_btn.grid(row=1, column=2, padx=(0, 14), pady=4)

        # 2. Processed / Archive Folder Field
        proc_lbl = ctk.CTkLabel(self.paths_card, text="Archive Folder:", font=ctk.CTkFont(weight="bold"))
        proc_lbl.grid(row=2, column=0, padx=14, pady=4, sticky="w")

        self.proc_entry = ctk.CTkEntry(
            self.paths_card,
            height=32,
            placeholder_text="Enter or browse destination Archive folder..."
        )
        self.proc_entry.grid(row=2, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.proc_entry.bind("<FocusOut>", self._on_field_change)
        self.proc_entry.bind("<KeyRelease>", self._on_field_change)

        proc_btn = ctk.CTkButton(
            self.paths_card,
            text="Browse...",
            width=80,
            height=32,
            command=self._browse_processed
        )
        proc_btn.grid(row=2, column=2, padx=(0, 14), pady=4)

        # 3. Master Spreadsheet File Field
        sheet_lbl = ctk.CTkLabel(self.paths_card, text="Master Spreadsheet:", font=ctk.CTkFont(weight="bold"))
        sheet_lbl.grid(row=3, column=0, padx=14, pady=4, sticky="w")

        self.sheet_entry = ctk.CTkEntry(
            self.paths_card,
            height=32,
            placeholder_text="Enter or browse path to Master Spreadsheet (.xlsx or .csv)..."
        )
        self.sheet_entry.grid(row=3, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.sheet_entry.bind("<FocusOut>", self._on_field_change)
        self.sheet_entry.bind("<KeyRelease>", self._on_field_change)

        sheet_btn = ctk.CTkButton(
            self.paths_card,
            text="Browse...",
            width=80,
            height=32,
            command=self._browse_spreadsheet
        )
        sheet_btn.grid(row=3, column=2, padx=(0, 14), pady=4)

        # Bottom row inside paths card: Quick helper links & save button
        paths_action_frame = ctk.CTkFrame(self.paths_card, fg_color="transparent")
        paths_action_frame.grid(row=4, column=0, columnspan=3, padx=14, pady=(6, 8), sticky="ew")

        save_cfg_btn = ctk.CTkButton(
            paths_action_frame,
            text="💾 Save Paths",
            width=130,
            height=28,
            fg_color="#3B8ED0",
            command=self._save_settings
        )
        save_cfg_btn.pack(side="left", padx=(0, 8))

        open_unproc_btn = ctk.CTkButton(
            paths_action_frame,
            text="📂 Open Unprocessed",
            width=160,
            height=28,
            fg_color="#4F5D75",
            command=self._open_unprocessed_folder
        )
        open_unproc_btn.pack(side="left", padx=4)

        open_sheet_btn = ctk.CTkButton(
            paths_action_frame,
            text="📊 Open Spreadsheet",
            width=150,
            height=28,
            fg_color="#2D6A4F",
            command=self._open_spreadsheet_file
        )
        open_sheet_btn.pack(side="left", padx=4)

        open_log_btn = ctk.CTkButton(
            paths_action_frame,
            text="📝 Open Logs.txt",
            width=130,
            height=28,
            fg_color="#4F5D75",
            command=self._open_log_file
        )
        open_log_btn.pack(side="left", padx=4)

        # ----------------- CONFIGURATION & CREDENTIALS CARD -----------------
        self.config_card = ctk.CTkFrame(self, corner_radius=10)
        self.config_card.grid(row=2, column=0, padx=16, pady=6, sticky="ew")
        self.config_card.grid_columnconfigure(1, weight=1)

        card_title = ctk.CTkLabel(
            self.config_card,
            text="Gemini AI Credentials & Model",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.grid(row=0, column=0, columnspan=3, padx=14, pady=(8, 4), sticky="w")

        # API Key Row
        key_lbl = ctk.CTkLabel(self.config_card, text="Gemini API Key:", font=ctk.CTkFont(weight="bold"))
        key_lbl.grid(row=1, column=0, padx=14, pady=4, sticky="w")

        key_input_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        key_input_frame.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="ew")
        key_input_frame.grid_columnconfigure(0, weight=1)

        self.api_key_entry = ctk.CTkEntry(
            key_input_frame,
            placeholder_text="Enter your Google Gemini API Key (e.g. AIzaSy...)",
            show="•",
            height=30
        )
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.api_key_entry.bind("<FocusOut>", self._on_field_change)

        self.show_key_btn = ctk.CTkButton(
            key_input_frame,
            text="Show",
            width=50,
            height=30,
            command=self._toggle_api_key_visibility
        )
        self.show_key_btn.grid(row=0, column=1)

        # Test Connection & Model Selection
        action_row = ctk.CTkFrame(self.config_card, fg_color="transparent")
        action_row.grid(row=1, column=2, padx=14, pady=4, sticky="e")

        self.test_btn = ctk.CTkButton(
            action_row,
            text="Test Connection",
            height=30,
            width=110,
            command=self._test_api_connection
        )
        self.test_btn.pack(side="left", padx=4)

        model_lbl = ctk.CTkLabel(action_row, text="Model:", font=ctk.CTkFont(weight="bold"))
        model_lbl.pack(side="left", padx=(10, 4))

        self.model_menu = ctk.CTkOptionMenu(
            action_row,
            values=AVAILABLE_MODELS,
            width=140,
            height=30,
            command=lambda m: self._on_field_change()
        )
        self.model_menu.pack(side="left")

        # Status text for connection test
        self.api_status_lbl = ctk.CTkLabel(
            self.config_card,
            text="",
            font=ctk.CTkFont(size=11)
        )
        self.api_status_lbl.grid(row=2, column=1, columnspan=2, padx=14, pady=(0, 6), sticky="w")

        # ----------------- ACTIVITY & CONTROL SECTION -----------------
        self.action_frame = ctk.CTkFrame(self, corner_radius=10)
        self.action_frame.grid(row=3, column=0, padx=16, pady=(6, 12), sticky="nsew")
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_rowconfigure(3, weight=1)

        # Controls Bar
        controls_bar = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        controls_bar.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
        controls_bar.grid_columnconfigure(2, weight=1)

        self.scan_btn = ctk.CTkButton(
            controls_bar,
            text="🔍 Scan Pending",
            width=130,
            height=34,
            command=self._manual_scan_pending
        )
        self.scan_btn.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.pending_badge = ctk.CTkLabel(
            controls_bar,
            text="Awaiting inputs...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3B8ED0"
        )
        self.pending_badge.grid(row=0, column=1, padx=4, sticky="w")

        self.start_btn = ctk.CTkButton(
            controls_bar,
            text="▶ Start Processing",
            width=160,
            height=34,
            fg_color="#2EA043",
            hover_color="#238636",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_processing
        )
        self.start_btn.grid(row=0, column=3, padx=6, sticky="e")

        self.stop_btn = ctk.CTkButton(
            controls_bar,
            text="⏹ Stop",
            width=90,
            height=34,
            fg_color="#DA3633",
            hover_color="#B62324",
            state="disabled",
            command=self._stop_processing
        )
        self.stop_btn.grid(row=0, column=4, padx=(0, 2), sticky="e")

        # Progress Bar and Status
        progress_box = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        progress_box.grid(row=1, column=0, padx=14, pady=(2, 6), sticky="ew")
        progress_box.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_box, height=10)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(2, 2))

        self.status_lbl = ctk.CTkLabel(
            progress_box,
            text="Ready.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_lbl.grid(row=1, column=0, sticky="w")

        # Log View Header & Actions
        log_header = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        log_header.grid(row=2, column=0, padx=14, pady=(4, 2), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        log_lbl = ctk.CTkLabel(log_header, text="Activity Log (Logs.txt)", font=ctk.CTkFont(weight="bold"))
        log_lbl.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            log_header,
            text="Clear View",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#4F5D75",
            command=self._clear_log_display
        )
        clear_btn.grid(row=0, column=1, padx=(0, 4), sticky="e")

        copy_btn = ctk.CTkButton(
            log_header,
            text="Copy Log",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#4F5D75",
            command=self._copy_log_display
        )
        copy_btn.grid(row=0, column=2, sticky="e")

        # Text Box for Logs with Native Text widget for color tagging
        self.log_textbox = ctk.CTkTextbox(
            self.action_frame,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_textbox.grid(row=3, column=0, padx=14, pady=(0, 12), sticky="nsew")

        # Configure color tags inside Tk text widget
        text_widget = self.log_textbox._textbox
        text_widget.tag_config("SUCCESS", foreground="#3FB950")
        text_widget.tag_config("WARNING", foreground="#D29922")
        text_widget.tag_config("ERROR", foreground="#F85149")
        text_widget.tag_config("INFO", foreground="#58A6FF")
        text_widget.tag_config("DEFAULT", foreground="#C9D1D9")

    def _populate_fields(self):
        """
        Populates fields with previous values if they exist in config.
        On initial execution, these will be empty, prompting user input.
        On subsequent executions, previous values are automatically autofilled.
        """
        api_key = self.config.get("gemini_api_key", "")
        unproc = self.config.get("unprocessed_folder", "")
        proc = self.config.get("processed_folder", "")
        sheet = self.config.get("spreadsheet_path", "")

        if api_key:
            self.api_key_entry.insert(0, api_key)
        if unproc:
            self.unproc_entry.insert(0, unproc)
        if proc:
            self.proc_entry.insert(0, proc)
        if sheet:
            self.sheet_entry.insert(0, sheet)

        saved_model = self.config.get("model", "gemini-2.5-flash")
        if saved_model in AVAILABLE_MODELS:
            self.model_menu.set(saved_model)

    def _auto_save_paths(self):
        """Silently auto-persists current path and credential values for subsequent executions."""
        self.config["unprocessed_folder"] = self.unproc_entry.get().strip()
        self.config["processed_folder"] = self.proc_entry.get().strip()
        self.config["spreadsheet_path"] = self.sheet_entry.get().strip()
        self.config["gemini_api_key"] = self.api_key_entry.get().strip()
        self.config["model"] = self.model_menu.get()
        save_config(self.config)

    def _on_field_change(self, event=None):
        self._auto_save_paths()
        self._quick_scan_badge()

    def _toggle_api_key_visibility(self):
        if self.api_key_entry.cget("show") == "•":
            self.api_key_entry.configure(show="")
            self.show_key_btn.configure(text="Hide")
        else:
            self.api_key_entry.configure(show="•")
            self.show_key_btn.configure(text="Show")

    def _change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.config["theme"] = new_theme
        save_config(self.config)

    def _browse_unprocessed(self):
        initial = self.unproc_entry.get().strip() or str(Path.home())
        selected = filedialog.askdirectory(title="Select Unprocessed Receipts Folder", initialdir=initial)
        if selected:
            self.unproc_entry.delete(0, "end")
            self.unproc_entry.insert(0, selected)
            self._on_field_change()

    def _browse_processed(self):
        initial = self.proc_entry.get().strip() or str(Path.home())
        selected = filedialog.askdirectory(title="Select Processed Archive Folder", initialdir=initial)
        if selected:
            self.proc_entry.delete(0, "end")
            self.proc_entry.insert(0, selected)
            self._on_field_change()

    def _browse_spreadsheet(self):
        initial = self.sheet_entry.get().strip() or str(Path.home())
        selected = filedialog.askopenfilename(
            title="Select Master Spreadsheet File",
            initialdir=os.path.dirname(initial) if initial else str(Path.home()),
            filetypes=[("Excel & CSV Files", "*.xlsx *.csv"), ("Excel Workbook", "*.xlsx"), ("CSV File", "*.csv"), ("All Files", "*.*")]
        )
        if selected:
            self.sheet_entry.delete(0, "end")
            self.sheet_entry.insert(0, selected)
            self._on_field_change()

    def _save_settings(self):
        self._auto_save_paths()
        messagebox.showinfo(
            "Settings Saved",
            "Your paths and settings have been saved and will be autofilled on all subsequent executions."
        )

    def _quick_scan_badge(self):
        folder_str = self.unproc_entry.get().strip()
        if not folder_str:
            self.pending_badge.configure(text="Awaiting folder inputs...", text_color="gray")
            self.status_lbl.configure(text="Please specify your Unprocessed Folder, Archive Folder, and Master Spreadsheet above.")
            return

        if not os.path.exists(folder_str):
            self.pending_badge.configure(text="Folder does not exist", text_color="red")
            self.status_lbl.configure(text=f"Directory not found: {folder_str}")
            return

        try:
            files = get_unprocessed_files(Path(folder_str))
            count = len(files)
            if count == 0:
                self.pending_badge.configure(text="0 receipts pending", text_color="gray")
                self.status_lbl.configure(text="Ready. 0 pending receipts in unprocessed folder.")
            else:
                self.pending_badge.configure(
                    text=f"📁 {count} receipt{'s' if count != 1 else ''} ready to process",
                    text_color="#3B8ED0"
                )
                self.status_lbl.configure(text=f"Ready. {count} pending receipt(s) found.")
        except Exception:
            self.pending_badge.configure(text="Error reading folder", text_color="red")

    def _manual_scan_pending(self):
        folder_str = self.unproc_entry.get().strip()
        if not folder_str or not os.path.exists(folder_str):
            messagebox.showwarning("Folder Not Found", "Please choose a valid Unprocessed Receipts folder.")
            return

        files = get_unprocessed_files(Path(folder_str))
        count = len(files)
        self.pending_badge.configure(
            text=f"📁 {count} receipt{'s' if count != 1 else ''} ready",
            text_color="#3B8ED0" if count > 0 else "gray"
        )
        
        # Log info message to Logs.txt
        sheet_path = self.sheet_entry.get().strip()
        logger = ReceiptLogger(sheet_path, self._append_log_line)
        logger.info(f"Scan completed: {count} pending receipts found to process.")
        self.status_lbl.configure(text=f"Scan complete: {count} pending file(s).")

    def _test_api_connection(self):
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            self.api_status_lbl.configure(text="❌ Please enter a Gemini API Key first.", text_color="#F85149")
            return

        self.api_status_lbl.configure(text="Testing connection...", text_color="gray")
        self.test_btn.configure(state="disabled")

        def _worker():
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                model_name = self.model_menu.get()
                resp = client.models.generate_content(
                    model=model_name,
                    contents="Say 'OK' in one word."
                )
                if resp.text:
                    self.after(0, lambda: self._on_test_result(True, f"✓ Connected successfully to {model_name}"))
                else:
                    self.after(0, lambda: self._on_test_result(False, "Received empty response from API."))
            except Exception as e:
                self.after(0, lambda: self._on_test_result(False, f"Connection failed: {str(e)}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_test_result(self, success: bool, msg: str):
        self.test_btn.configure(state="normal")
        if success:
            self.api_status_lbl.configure(text=msg, text_color="#3FB950")
            self._auto_save_paths()
        else:
            self.api_status_lbl.configure(text=f"❌ {msg}", text_color="#F85149")

    def _append_log_line(self, tag: str, log_line: str):
        def _insert():
            text_widget = self.log_textbox._textbox
            tag_name = tag.upper() if tag.upper() in ["SUCCESS", "WARNING", "ERROR", "INFO"] else "DEFAULT"
            text_widget.insert("end", log_line + "\n", tag_name)
            text_widget.see("end")
        self.after(0, _insert)

    def _clear_log_display(self):
        self.log_textbox.delete("1.0", "end")

    def _copy_log_display(self):
        content = self.log_textbox.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copied", "Log output copied to clipboard.")

    def _open_spreadsheet_file(self):
        path = self.sheet_entry.get().strip()
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
        else:
            messagebox.showwarning("File Not Found", "Spreadsheet file path is not set or does not exist.")

    def _open_log_file(self):
        sheet_path = self.sheet_entry.get().strip()
        if sheet_path:
            log_path = Path(sheet_path).parent / "Logs.txt"
            if log_path.exists():
                try:
                    os.startfile(str(log_path))
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open Logs.txt: {e}")
                    return
        messagebox.showwarning("Log Not Found", "Logs.txt has not been created yet in the spreadsheet folder.")

    def _open_unprocessed_folder(self):
        path = self.unproc_entry.get().strip()
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open directory: {e}")
        else:
            messagebox.showwarning("Folder Not Found", "Unprocessed folder path is not set or does not exist.")

    def _start_processing(self):
        if self.is_running:
            return

        api_key = self.api_key_entry.get().strip()
        unprocessed_folder = self.unproc_entry.get().strip()
        processed_folder = self.proc_entry.get().strip()
        spreadsheet_path = self.sheet_entry.get().strip()
        model_name = self.model_menu.get()

        # Validate inputs
        if not unprocessed_folder:
            messagebox.showerror("Folder Missing", "Please enter or browse for the Unprocessed Receipts folder.")
            return

        if not os.path.exists(unprocessed_folder):
            messagebox.showerror("Folder Error", f"Unprocessed receipts folder does not exist:\n{unprocessed_folder}")
            return

        if not processed_folder:
            messagebox.showerror("Folder Missing", "Please enter or browse for the Archive folder.")
            return

        if not spreadsheet_path:
            messagebox.showerror("Spreadsheet Missing", "Please enter or browse for the Master Spreadsheet file.")
            return

        if not os.path.exists(spreadsheet_path):
            messagebox.showerror("Spreadsheet Error", f"Spreadsheet file does not exist:\n{spreadsheet_path}")
            return

        if not api_key:
            messagebox.showerror("API Key Missing", "Please enter your Gemini API Key in the credentials field.")
            return

        # Check if spreadsheet is locked / open in Excel
        try:
            with open(spreadsheet_path, "a+b"):
                pass
        except PermissionError:
            messagebox.showerror(
                "Spreadsheet Locked",
                f"The spreadsheet '{Path(spreadsheet_path).name}' is currently open in Microsoft Excel or another program.\n\nPlease close Excel and try again."
            )
            return
        except Exception as e:
            messagebox.showerror("Spreadsheet Error", f"Cannot open spreadsheet for writing: {e}")
            return

        # Auto-save current inputs so subsequent executions autofill them
        self._auto_save_paths()

        # Setup execution state
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.scan_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_lbl.configure(text="Starting receipt processing batch...")

        # Initialize Logger and Processor
        logger = ReceiptLogger(spreadsheet_path, ui_callback=self._append_log_line)
        self.processor = ReceiptProcessor(
            unprocessed_folder=unprocessed_folder,
            processed_folder=processed_folder,
            spreadsheet_path=spreadsheet_path,
            api_key=api_key,
            model_name=model_name,
            logger=logger,
            progress_callback=self._update_progress
        )

        def _worker():
            try:
                summary = self.processor.run()
                self.after(0, lambda: self._on_processing_finished(summary))
            except Exception as e:
                self.after(0, lambda: self._on_processing_error(str(e)))

        self.processing_thread = threading.Thread(target=_worker, daemon=True)
        self.processing_thread.start()

    def _stop_processing(self):
        if self.processor and self.is_running:
            self.status_lbl.configure(text="Cancelling... finishing current receipt.")
            self.processor.cancel()
            self.stop_btn.configure(state="disabled")

    def _update_progress(self, current: int, total: int, filename: str, status_text: str):
        def _apply():
            if total > 0:
                self.progress_bar.set(current / total)
            self.status_lbl.configure(text=status_text)
        self.after(0, _apply)

    def _on_processing_finished(self, summary: dict):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.scan_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._quick_scan_badge()

        total = summary.get("total_found", 0)
        success = summary.get("success_count", 0)
        errors = summary.get("error_count", 0)
        warnings = summary.get("warning_count", 0)
        status = summary.get("status", "Completed")

        report_lines = [
            f"Status: {status}",
            f"Total Receipts Found: {total}",
            f"Successfully Processed & Moved: {success}",
            f"Errors / Aborted: {errors}",
            f"Warnings (Renamed): {warnings}"
        ]

        if summary.get("failures"):
            report_lines.append("\nFailures:")
            for f in summary["failures"]:
                report_lines.append(f" • {f['filename']}: {f['reason']}")

        report_msg = "\n".join(report_lines)

        if total == 0:
            self.status_lbl.configure(text="Scan completed: 0 pending receipts.")
        else:
            self.status_lbl.configure(
                text=f"Batch finished: {success} succeeded, {errors} failed."
            )
            messagebox.showinfo("Batch Summary", report_msg)

    def _on_processing_error(self, err_msg: str):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.scan_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._quick_scan_badge()
        self.status_lbl.configure(text=f"Execution error: {err_msg}")
        messagebox.showerror("Processing Error", f"An unexpected error occurred:\n{err_msg}")

def launch_app():
    app = ReceiptManagerApp()
    app.mainloop()

if __name__ == "__main__":
    launch_app()
