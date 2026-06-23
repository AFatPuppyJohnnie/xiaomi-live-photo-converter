#!/usr/bin/env python3
import json
import queue
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Xiaomi Motion Photo Converter"


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x520")
        self.minsize(680, 460)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready")
        self.events = queue.Queue()

        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        ttk.Label(root, text="Source folder").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(root, textvariable=self.input_dir).grid(row=0, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(root, text="Choose...", command=self.choose_input).grid(row=0, column=2, pady=(0, 8))

        ttk.Label(root, text="Output folder").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(root, textvariable=self.output_dir).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(root, text="Choose...", command=self.choose_output).grid(row=1, column=2, pady=(0, 8))

        ttk.Checkbutton(root, text="Preview only, do not write Live Photo pairs", variable=self.dry_run).grid(
            row=2, column=1, sticky="w", pady=(4, 12)
        )

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        actions.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(actions, text="Start conversion", command=self.start_conversion)
        self.start_button.grid(row=0, column=1, sticky="e")

        ttk.Label(root, textvariable=self.status).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 6))

        log_frame = ttk.Frame(root)
        log_frame.grid(row=5, column=0, columnspan=3, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=16, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def choose_input(self):
        path = filedialog.askdirectory(title="Choose source folder")
        if path:
            self.input_dir.set(path)

    def choose_output(self):
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_dir.set(path)

    def start_conversion(self):
        input_dir = Path(self.input_dir.get()).expanduser()
        output_dir = Path(self.output_dir.get()).expanduser()
        if not input_dir.is_dir():
            messagebox.showerror(APP_TITLE, "Choose a valid source folder.")
            return
        if not str(output_dir):
            messagebox.showerror(APP_TITLE, "Choose a valid output folder.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        report = output_dir / "conversion_report.jsonl"
        results = output_dir / "conversion_results.json"

        cmd = [
            sys.executable,
            str(Path(__file__).with_name("convert_xiaomi_motion_photo.py")),
            "--input-dir",
            str(input_dir),
            "--out",
            str(output_dir),
            "--report",
            str(report),
        ]
        if self.dry_run.get():
            cmd.append("--dry-run")

        self.start_button.configure(state="disabled")
        self.status.set("Running...")
        self._clear_log()
        self._append_log(f"Source: {input_dir}\n")
        self._append_log(f"Output: {output_dir}\n")
        self._append_log(f"Report: {report}\n\n")

        worker = threading.Thread(target=self._run_worker, args=(cmd, results), daemon=True)
        worker.start()

    def _run_worker(self, cmd, results_path):
        try:
            with results_path.open("w", encoding="utf-8") as results_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=results_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                assert process.stderr is not None
                for line in process.stderr:
                    self.events.put(("log", line))
                code = process.wait()
            self.events.put(("done", code, results_path))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "log":
                    self._append_log(event[1])
                elif kind == "done":
                    self._handle_done(event[1], event[2])
                elif kind == "error":
                    self._handle_error(event[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle_done(self, code, results_path):
        self.start_button.configure(state="normal")
        if code != 0:
            self.status.set("Finished with errors")
            messagebox.showerror(APP_TITLE, f"Conversion finished with exit code {code}.")
            return

        summary = self._summarize(results_path)
        self.status.set(summary)
        self._append_log("\n" + summary + "\n")
        messagebox.showinfo(APP_TITLE, summary)

    def _handle_error(self, message):
        self.start_button.configure(state="normal")
        self.status.set("Error")
        self._append_log("\nError: " + message + "\n")
        messagebox.showerror(APP_TITLE, message)

    def _summarize(self, results_path):
        try:
            rows = json.loads(results_path.read_text(encoding="utf-8"))
            counts = Counter(row.get("status", "unknown") for row in rows)
            return (
                f"Done. Total: {len(rows)}, converted: {counts.get('converted', 0)}, "
                f"skipped: {counts.get('skipped', 0)}, failed: {counts.get('failed', 0)}"
            )
        except Exception:
            return "Done. Could not summarize result file."

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")


if __name__ == "__main__":
    ConverterApp().mainloop()
