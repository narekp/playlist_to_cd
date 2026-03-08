import os
import subprocess

from core.naming import safe_name
from core.constants import (
    AUDIO_CD_SAMPLE_RATE,
    AUDIO_CD_CHANNELS,
    AUDIO_CD_SAMPLE_FORMAT,
)


def convert_to_wav(mp3_path, wav_path, stop_flag):
    if stop_flag.is_set():
        raise Exception("Stopped")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        mp3_path,
        "-ar",
        AUDIO_CD_SAMPLE_RATE,
        "-ac",
        AUDIO_CD_CHANNELS,
        "-sample_fmt",
        AUDIO_CD_SAMPLE_FORMAT,
        wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip() or "WAV conversion failed")


def renumber_wavs(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith(".wav")]
    files.sort()
    count = len(files)
    if count == 0:
        return
    pad = 3 if count >= 100 else 2
    for i, filename in enumerate(files, start=1):
        new_name = f"{i:0{pad}d}.wav"
        src = os.path.join(folder, filename)
        dst = os.path.join(folder, new_name)
        if src != dst:
            os.rename(src, dst)


def run_audio_cd_pipeline(processed_dir, log_queue, stop_flag):
    audio_dir = os.path.join(processed_dir, "audio_cd_ready")
    os.makedirs(audio_dir, exist_ok=True)

    mp3_files = sorted(
        f for f in os.listdir(processed_dir) if f.lower().endswith(".mp3")
    )
    count = len(mp3_files)
    pad = 3 if count >= 100 else 2

    for i, filename in enumerate(mp3_files, start=1):
        if stop_flag.is_set():
            raise Exception("Stopped")
        mp3_path = os.path.join(processed_dir, filename)
        base = os.path.splitext(filename)[0]
        title = safe_name(base)
        wav_name = f"{i:0{pad}d} - {title}.wav"
        wav_path = os.path.join(audio_dir, wav_name)
        log_queue.put(f"[AUDIO] Converting to WAV: {filename} -> {wav_name}")
        convert_to_wav(mp3_path, wav_path, stop_flag)

    total_bytes = 0
    for f in os.listdir(audio_dir):
        if f.lower().endswith(".wav"):
            total_bytes += os.path.getsize(os.path.join(audio_dir, f))
    total_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
    return total_mb

