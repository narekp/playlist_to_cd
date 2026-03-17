#!/usr/bin/env python3
import csv
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox, scrolledtext, ttk
from urllib.parse import urlparse

from core.artists import get_duration_ms, make_track_key
from core.ffmpeg_utils import (
    convert_to_bitrate,
    estimate_required_bitrate,
    get_total_size,
    renumber_files,
    set_metadata,
    verify_duration,
)
from core.naming import format_artists_for_filename, safe_name
from core.query import build_query_variants
from sources.csv_source import load_tracks_from_csv

# =====================================
# Media Batch Processor MVP (v2.2 – Skip invalid CSV rows)
# =====================================
# Reports reflect only this run. Resume state stored in state.json.

MAX_PRIMARY_CANDIDATES = 3
MAX_FALLBACK_CANDIDATES = 3   # kept for compatibility, not used in new flow

def get_run_folder_name(csv_path):
    """
    Use the CSV filename (without extension) as the output folder name.
    Example: /path/Raggamuffin.csv -> Raggamuffin
    """
    base = os.path.splitext(os.path.basename(csv_path))[0]
    return safe_name(base) or "processed_media"

def get_candidate_metadata(query, candidate_num, stop_flag):
    """Retrieve metadata (url, title, duration) without downloading."""
    if stop_flag.is_set():
        return None
    search_str = f"ytsearch{candidate_num}:{query}"
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--dump-json",
        "--skip-download",
        "--playlist-start", str(candidate_num),
        "--playlist-end", str(candidate_num),
        search_str
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not result.stdout:
            return None
        data = json.loads(result.stdout.strip().split('\n')[0])
        url = data.get('webpage_url') or data.get('url')
        title = data.get('title', '')
        duration = data.get('duration')
        if url and duration is not None:
            return {'url': url, 'title': title, 'duration': float(duration)}
    except (json.JSONDecodeError, subprocess.TimeoutExpired, KeyError, ValueError):
        pass
    return None

def download_from_url(candidate_url, out_path, stop_flag):
    """
    Download audio from the exact candidate_url.
    Before downloading, remove any stale file at out_path with any extension.
    """
    if stop_flag.is_set():
        raise Exception("Stopped")

    # Clean up any leftover file from a previous attempt
    for ext in [".mp3", ".webm", ".opus", ".m4a", ".aac"]:
        stale = out_path + ext
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass

    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", f"{out_path}.%(ext)s",
        candidate_url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip() or "Download failed")

    for ext in [".mp3", ".webm", ".opus"]:
        candidate = out_path + ext
        if os.path.exists(candidate):
            mp3_path = out_path + ".mp3"
            if ext != ".mp3":
                cmd_convert = ['ffmpeg', '-y', '-i', candidate, mp3_path]
                convert_result = subprocess.run(cmd_convert, capture_output=True, text=True)
                if convert_result.returncode == 0:
                    os.remove(candidate)
                else:
                    raise Exception(f"Conversion failed: {convert_result.stderr}")
            else:
                mp3_path = candidate
            if os.path.exists(mp3_path):
                return mp3_path
            else:
                raise Exception("MP3 not created")
    raise Exception("No file saved")

def process_folder(folder, log_queue, stop_flag, start_bitrate):
    """Post‑processing: reduce bitrate if needed, apply metadata, renumber."""
    log_queue.put("[POST] Starting post-processing...")
    total_size = get_total_size(folder)
    log_queue.put(f"[POST] Initial accepted MP3 total: {total_size:.2f} MB")

    if total_size <= 699:
        set_metadata(folder, stop_flag)
        renumber_files(folder)
        final_size = get_total_size(folder)
        log_queue.put(f"[POST] Final MP3 total: {final_size:.2f} MB")
        return

    bitrates = [320, 256, 192, 160, 128]
    # Find index of start_bitrate (default to 0 if not found)
    try:
        start_index = bitrates.index(start_bitrate)
    except ValueError:
        start_index = 0
    last_temp = None
    final_temp_size = None

    for br in bitrates[start_index:]:
        log_queue.put(f"[POST] Trying bitrate pass: {br} kbps")
        temp_folder = folder + f'_temp_{br}'
        convert_to_bitrate(folder, temp_folder, br, stop_flag)
        temp_size = get_total_size(temp_folder)
        log_queue.put(f"[POST] After {br} kbps: {temp_size:.2f} MB")
        if temp_size <= 699:
            last_temp = temp_folder
            final_temp_size = temp_size
            break
        if br == 128:
            last_temp = temp_folder
            final_temp_size = temp_size
        else:
            shutil.rmtree(temp_folder)

    if last_temp:
        if final_temp_size > 699:
            log_queue.put(
                f"[POST] WARNING: Even at 128 kbps, final size is still {final_temp_size:.2f} MB and exceeds the 700 MB target."
            )
        for f in os.listdir(folder):
            if f.endswith('.mp3'):
                os.remove(os.path.join(folder, f))
        for f in os.listdir(last_temp):
            shutil.move(os.path.join(last_temp, f), folder)
        shutil.rmtree(last_temp)
    else:
        log_queue.put("[POST] WARNING: Could not produce a valid reduced-size output set.")

    log_queue.put("[POST] Applying metadata...")
    set_metadata(folder, stop_flag)
    log_queue.put("[POST] Renumbering files...")
    renumber_files(folder)

    final_size = get_total_size(folder)
    log_queue.put(f"[POST] Final MP3 total: {final_size:.2f} MB")

def check_dependencies():
    """Return (True, []) if all deps found, else (False, [missing_names])."""
    deps = {'yt-dlp': 'yt-dlp --version', 'ffmpeg': 'ffmpeg -version', 'ffprobe': 'ffprobe -version'}
    missing = []
    for name, cmd in deps.items():
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode != 0:
            missing.append(name)
    return (True, []) if not missing else (False, missing)


def _format_missing_deps_message(missing):
    return (
        f"Missing required dependencies: {', '.join(missing)}\n\n"
        "The app could not find these tools on your system PATH.\n"
        "Please install them (e.g., using Homebrew: 'brew install ffmpeg yt-dlp')\n"
        "or ensure they are located in /opt/homebrew/bin or /usr/local/bin."
    )


class App:
    def __init__(self, root):
        self.root = root
        root.title("Playlist to CD")
        root.geometry("700x650")
        root.minsize(600, 550)

        ok, missing = check_dependencies()
        if not ok:
            messagebox.showerror("Error", _format_missing_deps_message(missing))
            sys.exit(1)

        main_frame = tk.Frame(root, padx=12, pady=10)
        main_frame.pack(fill=tk.X)

        # Source: Playlist URL + CSV file
        source_frame = tk.LabelFrame(main_frame, text="Source", padx=8, pady=6)
        source_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(source_frame, text="Playlist URL:").pack(pady=4)
        self.url_entry = tk.Entry(source_frame, width=50)
        self.url_entry.pack(pady=4)
        tk.Button(source_frame, text="Open Exportify for CSV", command=self.open_exportify).pack(pady=4)
        tk.Label(source_frame, text="CSV File:").pack(pady=4)
        self.csv_entry = tk.Entry(source_frame, width=50)
        self.csv_entry.pack(pady=4)
        tk.Button(source_frame, text="Browse CSV", command=self.browse_csv).pack(pady=4)

        # Destination: Output folder
        dest_frame = tk.LabelFrame(main_frame, text="Output", padx=8, pady=6)
        dest_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(dest_frame, text="Output Folder:").pack(pady=4)
        self.out_entry = tk.Entry(dest_frame, width=50)
        self.out_entry.pack(pady=4)
        tk.Button(dest_frame, text="Browse Folder", command=self.browse_folder).pack(pady=4)

        # Mode and actions
        mode_actions_frame = tk.LabelFrame(main_frame, text="Mode & actions", padx=8, pady=6)
        mode_actions_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(mode_actions_frame, text="Output Mode:").pack(pady=4)
        self.mode_var = tk.StringVar(value="mp3")
        mode_frame = tk.Frame(mode_actions_frame)
        mode_frame.pack(pady=4)
        tk.Radiobutton(mode_frame, text="MP3 CD", variable=self.mode_var, value="mp3").pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Audio CD", variable=self.mode_var, value="audio").pack(side=tk.LEFT)
        self.start_btn = tk.Button(mode_actions_frame, text="Start", command=self.start_process)
        self.start_btn.pack(pady=4)
        self.stop_btn = tk.Button(mode_actions_frame, text="Stop", command=self.stop_process, state='disabled')
        self.stop_btn.pack(pady=4)

        # Progress
        progress_frame = tk.LabelFrame(main_frame, text="Progress", padx=8, pady=6)
        progress_frame.pack(fill=tk.X, pady=(0, 8))
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress.pack(pady=4, fill=tk.X)

        # Log area (expands on resize)
        log_frame = tk.LabelFrame(root, text="Log", padx=6, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.log = scrolledtext.ScrolledText(log_frame, height=10)
        self.log.tag_configure("ok", foreground="#2e8b57")
        self.log.tag_configure("warn", foreground="#b8860b")
        self.log.tag_configure("error", foreground="#cc0000")
        self.log.pack(fill=tk.BOTH, expand=True)

        self.log_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.finished_flag = threading.Event()
        self.executor = None
        self.root.after(100, self.process_queue)

        # Set size and position after layout so the window opens centered
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        width, height = 700, 650
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.update_idletasks()
        root.lift()
        root.attributes("-topmost", True)
        root.attributes("-topmost", False)

    def _tag_for(self, msg):
        if msg.startswith("[OK]") or msg.startswith("[META-ACCEPT]") or msg == "Completed successfully.":
            return "ok"
        if "WARNING" in msg or msg.startswith("[SKIP]") or msg.startswith("[SKIP-INVALID-ROW]") or msg.startswith("[REJECTED]") or msg.startswith("[META-REJECT]") or msg.startswith("Completed with issues"):
            return "warn"
        if msg.startswith("[FAILED]") or msg.startswith("[DOWNLOAD-FAIL]") or msg.startswith("[POST-REJECT]") or msg.startswith("Post-processing failed") or msg.startswith("Worker error"):
            return "error"
        return None

    def process_queue(self):
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                if msg.startswith("[PROGRESS MAX]"):
                    self.progress['maximum'] = int(msg.split()[-1])
                elif msg.startswith("[PROGRESS SET]"):
                    self.progress['value'] = int(msg.split()[-1])
                elif msg == "[PROGRESS INC]":
                    self.progress['value'] += 1
                else:
                    tag = self._tag_for(msg)
                    if tag:
                        self.log.insert(tk.END, msg + '\n', tag)
                    else:
                        self.log.insert(tk.END, msg + '\n')
                    self.log.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def open_exportify(self):
        url = (self.url_entry.get() or "").strip()
        if url:
            parsed = urlparse(url)
            playlist_id = parsed.path.rstrip("/").split("/")[-1]
            if playlist_id:
                export_url = f"https://exportify.net/?playlist={playlist_id}"
                webbrowser.open(export_url)
                self.log_queue.put("Opened Exportify with playlist—export CSV, then use Browse CSV below.")
                return
        webbrowser.open("https://exportify.net/")
        self.log_queue.put("Opened Exportify. Paste your Spotify playlist link there, export CSV, then use Browse CSV below.")

    def browse_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv")],
            initialdir=os.path.expanduser("~/Downloads"),
        )
        if path:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, path)

    def browse_folder(self):
        path = filedialog.askdirectory(initialdir=os.path.expanduser("~/Desktop"))
        if path:
            self.out_entry.delete(0, tk.END)
            self.out_entry.insert(0, path)

    def start_process(self):
        csv_path = self.csv_entry.get()
        out_dir = self.out_entry.get()
        if not csv_path or not out_dir or not os.access(out_dir, os.W_OK):
            messagebox.showerror("Error", "Invalid CSV or output folder (must be writable).")
            return
        if not os.path.exists(csv_path):
            messagebox.showerror("Error", "CSV not found.")
            return
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.stop_flag.clear()
        self.finished_flag.clear()
        process_thread = threading.Thread(target=self.run_process, args=(csv_path, out_dir), daemon=True)
        process_thread.start()

    def stop_process(self):
        self.stop_flag.set()
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)
        self.log_queue.put("Stopping new tasks...")

    def ask_user_on_main_thread(self, kind, title, message):
        result_queue = queue.Queue()

        def _show():
            try:
                if kind == "yesno":
                    result_queue.put(messagebox.askyesno(title, message))
                elif kind == "error":
                    messagebox.showerror(title, message)
                    result_queue.put(True)
                elif kind == "info":
                    messagebox.showinfo(title, message)
                    result_queue.put(True)
                else:
                    result_queue.put(None)
            except Exception as e:
                result_queue.put(e)

        self.root.after(0, _show)
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return result

    def run_process(self, csv_path, out_dir):
        # Use CSV filename as output folder name
        run_folder_name = get_run_folder_name(csv_path)
        processed_dir = os.path.join(out_dir, run_folder_name)
        try:
            os.makedirs(processed_dir, exist_ok=True)
            self.log_queue.put("Note: Reports will reflect this run only. Resume state is tracked in state.json.")

            state_file = os.path.join(processed_dir, "state.json")
            downloaded_set = set()
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    downloaded_set = set(json.load(f))

            valid_tracks, invalid_rows_list = load_tracks_from_csv(csv_path)
            invalid_rows = len(invalid_rows_list)

            accepted = 0
            rejected = 0
            failed = 0
            skipped = 0
            total_duration_sec = 0.0
            accepted_duration_sec = 0.0

            # Build average from known durations only (excluding invalid rows)
            known_duration_secs = []
            for row in valid_tracks:
                duration_str = get_duration_ms(row)
                try:
                    duration_val = int(duration_str)
                    if duration_val > 0:
                        known_duration_secs.append(duration_val / 1000.0)
                except (ValueError, TypeError):
                    pass

            avg_known_duration_sec = (
                sum(known_duration_secs) / len(known_duration_secs)
                if known_duration_secs else 180.0
            )

            # Write invalid rows to a separate CSV
            if invalid_rows > 0:
                invalid_file = os.path.join(processed_dir, "invalid_input_rows.csv")
                all_rows = valid_tracks + invalid_rows_list
                fieldnames = list(all_rows[0].keys()) if all_rows else []
                with open(invalid_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in invalid_rows_list:
                        writer.writerow(row)
                        self.log_queue.put(f"[SKIP-INVALID-ROW] Missing track/artist – see {invalid_file}")

            tracks = valid_tracks
            total_valid = len(tracks)

            for row in tracks:
                duration_str = get_duration_ms(row)
                try:
                    duration_val = int(duration_str)
                    duration_for_estimate_sec = (
                        duration_val / 1000.0 if duration_val > 0 else avg_known_duration_sec
                    )
                except (ValueError, TypeError):
                    duration_for_estimate_sec = avg_known_duration_sec

                total_duration_sec += duration_for_estimate_sec

                key = make_track_key(row)
                display_artists = format_artists_for_filename(row.get("Artist Name(s)", ""))
                base_name = safe_name(f"{display_artists} - {row.get('Track Name', '')}")
                out_path = os.path.join(processed_dir, base_name + ".mp3")
                if key in downloaded_set and os.path.exists(out_path):
                    skipped += 1
                    accepted_duration_sec += duration_for_estimate_sec
                    self.log_queue.put(f"[SKIP] {row.get('Artist Name(s)', '')} - {row.get('Track Name', '')}")

            self.log_queue.put(f"[PROGRESS MAX] {total_valid}")
            self.log_queue.put(f"[PROGRESS SET] {skipped}")

            # Pre‑flight estimate (based on valid total with imputation)
            if total_duration_sec > 0:
                required_kbps = estimate_required_bitrate(total_duration_sec)
                self.log_queue.put(f"[ESTIMATE] Required avg bitrate for 700 MB (valid tracks with imputation): ~{required_kbps} kbps")
                if required_kbps < 128:
                    choice = self.ask_user_on_main_thread(
                        "yesno",
                        "Quality Warning",
                        f"This collection is estimated to need about {required_kbps} kbps to fit into 700 MB.\n\n"
                        "128 kbps is the minimum quality floor for this app.\n\n"
                        "Yes = continue at 128 kbps if needed, even if the final size still exceeds 700 MB\n"
                        "No = cancel this run"
                    )
                    if not choice:
                        self.log_queue.put("Cancelled due to bitrate warning.")
                        return

            lock = threading.Lock()
            down_queue = queue.Queue()
            fail_queue = queue.Queue()
            reject_queue = queue.Queue()

            def writer_thread():
                down_file = open(os.path.join(processed_dir, "downloaded_tracks.csv"), "w", newline="", encoding="utf-8")
                fail_file = open(os.path.join(processed_dir, "failed_downloads.csv"), "w", newline="", encoding="utf-8")
                reject_file = open(os.path.join(processed_dir, "rejected_tracks.csv"), "w", newline="", encoding="utf-8")
                down_writer = csv.DictWriter(down_file, fieldnames=["Track Name", "Artist Name(s)", "ISRC", "Saved File"])
                fail_writer = csv.DictWriter(fail_file, fieldnames=["Track Name", "Artist Name(s)", "ISRC", "Error"])
                reject_writer = csv.DictWriter(reject_file, fieldnames=["Track Name", "Artist Name(s)", "ISRC", "Expected Duration (ms)", "Saved File", "Reason"])
                down_writer.writeheader()
                fail_writer.writeheader()
                reject_writer.writeheader()
                while True:
                    if self.finished_flag.is_set() and down_queue.empty() and fail_queue.empty() and reject_queue.empty():
                        break
                    try:
                        item = down_queue.get(timeout=1)
                        down_writer.writerow(item)
                        down_file.flush()
                    except queue.Empty:
                        pass
                    try:
                        item = fail_queue.get(timeout=1)
                        fail_writer.writerow(item)
                        fail_file.flush()
                    except queue.Empty:
                        pass
                    try:
                        item = reject_queue.get(timeout=1)
                        reject_writer.writerow(item)
                        reject_file.flush()
                    except queue.Empty:
                        pass
                down_file.close()
                fail_file.close()
                reject_file.close()

            writer = threading.Thread(target=writer_thread, daemon=True)
            writer.start()

            def download_track(row, stop_flag):
                nonlocal accepted_duration_sec
                if stop_flag.is_set():
                    return False, "stopped"
                track = row.get("Track Name", "")
                artist = row.get("Artist Name(s)", "")
                key = make_track_key(row)
                duration_str = get_duration_ms(row)
                isrc = row.get("ISRC", "")
                display_artists = format_artists_for_filename(artist)
                base_name = safe_name(f"{display_artists} - {track}")
                out_path = os.path.join(processed_dir, base_name)
                final_file = out_path + ".mp3"
                if key in downloaded_set and os.path.exists(final_file):
                    return False, "skip"

                # Compute expected seconds; if missing/invalid, use the run average for estimation
                try:
                    expected_sec = int(duration_str) / 1000.0 if duration_str else None
                except ValueError:
                    expected_sec = None

                duration_for_estimate_sec = (
                    expected_sec if expected_sec is not None else avg_known_duration_sec
                )

                # Build list of query variants
                query_variants = build_query_variants(artist, track)

                any_rejection = False

                # Try each query variant in order
                for variant_idx, query in enumerate(query_variants, 1):
                    self.log_queue.put(f"[QUERY] variant {variant_idx}: {query}")

                    # Try up to MAX_PRIMARY_CANDIDATES results for this query
                    for i in range(1, MAX_PRIMARY_CANDIDATES + 1):
                        if stop_flag.is_set():
                            return False, "stopped"
                        self.log_queue.put(f"[TRY] variant {variant_idx} candidate {i} for {artist} - {track}")

                        meta = get_candidate_metadata(query, i, stop_flag)
                        if meta is None:
                            self.log_queue.put(f"[META] variant {variant_idx} candidate {i} – metadata lookup failed")
                            continue

                        # Screen duration (guard against zero division)
                        if expected_sec is not None and expected_sec > 0:
                            if abs(meta['duration'] - expected_sec) / expected_sec > 0.10:
                                self.log_queue.put(f"[META-REJECT] variant {variant_idx} candidate {i} duration {meta['duration']:.1f}s outside ±10%")
                                any_rejection = True
                                continue
                        else:
                            # No expected duration: only allow if ≤15 min
                            if meta['duration'] > 900:
                                self.log_queue.put(f"[META-REJECT] variant {variant_idx} candidate {i} duration {meta['duration']:.1f}s > 15 min (CSV missing)")
                                any_rejection = True
                                continue

                        self.log_queue.put(f"[META-ACCEPT] variant {variant_idx} candidate {i} duration {meta['duration']:.1f}s")

                        try:
                            saved = download_from_url(meta['url'], out_path, stop_flag)
                        except Exception as e:
                            self.log_queue.put(f"[DOWNLOAD-FAIL] variant {variant_idx} candidate {i} -> {e}")
                            continue

                        if verify_duration(saved, duration_str, stop_flag):
                            with lock:
                                downloaded_set.add(key)
                                accepted_duration_sec += duration_for_estimate_sec
                            down_queue.put({"Track Name": track, "Artist Name(s)": artist, "ISRC": isrc, "Saved File": saved})
                            self.log_queue.put(f"[OK] {artist} - {track}")
                            time.sleep(1)
                            return True, "accepted"
                        else:
                            self.log_queue.put(f"[POST-REJECT] variant {variant_idx} candidate {i} failed final duration check")
                            if os.path.exists(saved):
                                os.remove(saved)
                            any_rejection = True

                # All variants exhausted
                if any_rejection:
                    reject_queue.put({
                        "Track Name": track,
                        "Artist Name(s)": artist,
                        "ISRC": isrc,
                        "Expected Duration (ms)": duration_str,
                        "Saved File": "",
                        "Reason": "Duration mismatch on all candidates"
                    })
                    self.log_queue.put(f"[REJECTED] {artist} - {track} (no candidate passed duration)")
                    return False, "rejected"
                else:
                    fail_queue.put({"Track Name": track, "Artist Name(s)": artist, "ISRC": isrc, "Error": "No usable download"})
                    self.log_queue.put(f"[FAILED] {artist} - {track} (no usable download)")
                    return False, "failed"

            with ThreadPoolExecutor(max_workers=4) as executor:
                self.executor = executor
                futures = [
                    executor.submit(download_track, row, self.stop_flag)
                    for row in tracks
                    if make_track_key(row) not in downloaded_set
                    or not os.path.exists(
                        os.path.join(
                            processed_dir,
                            safe_name(f"{format_artists_for_filename(row.get('Artist Name(s)', ''))} - {row.get('Track Name', '')}") + ".mp3"
                        )
                    )
                ]
                for future in as_completed(futures):
                    try:
                        success, status = future.result()
                        if success and status == "accepted":
                            accepted += 1
                        elif status == "rejected":
                            rejected += 1
                        elif status == "failed":
                            failed += 1

                        if status in {"accepted", "rejected", "failed"}:
                            self.log_queue.put("[PROGRESS INC]")
                    except CancelledError:
                        pass
                    except Exception as e:
                        self.log_queue.put(f"Worker error: {e}")
                    with lock:
                        with open(state_file, 'w') as f:
                            json.dump(list(downloaded_set), f)
                    if self.stop_flag.is_set():
                        break

            self.finished_flag.set()
            writer.join()

            if not self.stop_flag.is_set():
                summary = f"Requested (valid): {total_valid}\nAccepted: {accepted}\nRejected: {rejected}\nFailed: {failed}\nSkipped: {skipped}\nInvalid rows ignored: {invalid_rows}"
                self.log_queue.put(summary)

                self.log_queue.put("Download phase complete. Starting post-processing...")
                if accepted > 0:
                    mode = self.mode_var.get()
                    if mode == "mp3":
                        from modes.mp3_cd import run_mp3_pipeline
                        final_size = run_mp3_pipeline(processed_dir, self.log_queue, self.stop_flag, accepted_duration_sec)
                    else:  # audio
                        from modes.audio_cd import run_audio_cd_pipeline
                        final_size = run_audio_cd_pipeline(processed_dir, self.log_queue, self.stop_flag)

                    try:
                        self.log_queue.put(f"[POST] Final MP3 total: {final_size:.2f} MB")

                        if final_size <= 699:
                            self.log_queue.put("Completed successfully.")
                            popup_title = "Done" if rejected == 0 and failed == 0 else "Completed with issues"
                            popup_msg = f"{summary}\n\nFinal size: {final_size:.2f} MB (under 700 MB).\nAll processing finished."
                        else:
                            self.log_queue.put("Completed with issues: final audio size exceeds 699 MB target.")
                            popup_title = "Completed with issues"
                            popup_msg = f"{summary}\n\nFinal size: {final_size:.2f} MB exceeds 700 MB target.\nAll processing finished."

                        self.ask_user_on_main_thread("info", popup_title, popup_msg)
                    except Exception as e:
                        self.log_queue.put(f"Post-processing failed: {e}")
                        self.ask_user_on_main_thread("error", "Post-processing failed", str(e))
                else:
                    self.log_queue.put("No valid files were accepted. Post-processing skipped.")
                    self.ask_user_on_main_thread(
                        "info",
                        "No Valid Files",
                        f"No valid files were accepted after duration validation.\n\n{summary}"
                    )

        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
            self.root.after(0, lambda: self.stop_btn.config(state='disabled'))
            if processed_dir and os.path.isdir(processed_dir):
                self.root.after(300, self.dump_log, processed_dir)

    def dump_log(self, processed_dir):
        def check_and_dump():
            if self.log_queue.empty():
                try:
                    log_text = self.log.get("1.0", tk.END)
                    with open(os.path.join(processed_dir, "process_log.txt"), 'w', encoding='utf-8') as f:
                        f.write(log_text)
                except Exception:
                    pass
            else:
                self.root.after(100, check_and_dump)
        check_and_dump()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()