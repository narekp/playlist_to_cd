import os
import shutil

from core.constants import MP3_BITRATE_LADDER_KBPS, MP3_CD_TARGET_MB
from core.ffmpeg_utils import (
    convert_to_bitrate,
    estimate_required_bitrate,
    get_total_size,
    renumber_files,
    set_metadata,
)


def process_mp3_folder(folder, log_queue, stop_flag, start_bitrate):
    """Post‑processing: reduce bitrate if needed, apply metadata, renumber."""
    log_queue.put("[POST] Starting post-processing...")
    total_size = get_total_size(folder)
    log_queue.put(f"[POST] Initial accepted MP3 total: {total_size:.2f} MB")

    if total_size <= MP3_CD_TARGET_MB:
        set_metadata(folder, stop_flag)
        renumber_files(folder)
        final_size = get_total_size(folder)
        log_queue.put(f"[POST] Final MP3 total: {final_size:.2f} MB")
        return

    bitrates = MP3_BITRATE_LADDER_KBPS
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
        if temp_size <= MP3_CD_TARGET_MB:
            last_temp = temp_folder
            final_temp_size = temp_size
            break
        if br == MP3_BITRATE_LADDER_KBPS[-1]:
            last_temp = temp_folder
            final_temp_size = temp_size
        else:
            shutil.rmtree(temp_folder)

    if last_temp:
        if final_temp_size > MP3_CD_TARGET_MB:
            log_queue.put(
                f"[POST] WARNING: Even at {MP3_BITRATE_LADDER_KBPS[-1]} kbps, final size is still {final_temp_size:.2f} MB and exceeds the 700 MB target."
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


def run_mp3_pipeline(processed_dir, log_queue, stop_flag, accepted_duration_sec):
    required_kbps = estimate_required_bitrate(accepted_duration_sec)
    cushioned = int(required_kbps * 0.95)
    bitrates = MP3_BITRATE_LADDER_KBPS
    start_bitrate = 128
    for br in bitrates:
        if br <= cushioned:
            start_bitrate = br
            break
    log_queue.put(
        f"[POST] Based on accepted total duration ({accepted_duration_sec/3600:.2f}h), "
        f"required ~{required_kbps} kbps. Starting at {start_bitrate} kbps."
    )
    process_mp3_folder(processed_dir, log_queue, stop_flag, start_bitrate)
    final_size = get_total_size(processed_dir)
    return final_size

