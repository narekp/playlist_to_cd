import os
import shutil
import subprocess

from .naming import format_artists_for_metadata


def verify_duration(file_path, expected_ms, stop_flag):
    if stop_flag.is_set():
        raise Exception("Stopped")

    try:
        expected_int = int(expected_ms) if expected_ms else 0
    except ValueError:
        expected_int = 0

    if expected_int == 0:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                actual_sec = float(result.stdout.strip())
                if actual_sec <= 900:
                    return True
            except ValueError:
                pass
        return False

    expected_sec = expected_int / 1000.0
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            actual_sec = float(result.stdout.strip())
            if abs(actual_sec - expected_sec) / expected_sec <= 0.10:
                return True
        except ValueError:
            pass
    return False


def get_total_size(folder):
    total = 0
    for file in os.listdir(folder):
        if file.endswith('.mp3'):
            total += os.path.getsize(os.path.join(folder, file))
    return total / (1024 * 1024)


def estimate_required_bitrate(total_duration_sec, target_mb=699):
    if total_duration_sec <= 0:
        return 320
    target_bytes = target_mb * 1024 * 1024
    overhead_factor = 1.1
    required_kbps = (target_bytes * 8 / total_duration_sec / 1000) / overhead_factor
    return int(required_kbps)


def convert_to_bitrate(original_folder, temp_folder, bitrate, stop_flag):
    """Convert all MP3s in original_folder to a given bitrate in temp_folder."""
    if stop_flag.is_set():
        raise Exception("Stopped")

    # Ensure a clean temp folder: remove any stale leftover from previous runs
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    os.makedirs(temp_folder, exist_ok=True)

    for file in os.listdir(original_folder):
        if stop_flag.is_set():
            raise Exception("Stopped")
        if file.endswith('.mp3'):
            input_path = os.path.join(original_folder, file)
            output_path = os.path.join(temp_folder, file)
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-b:a', f'{bitrate}k',
                '-ar', '44100',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Conversion failed: {result.stderr}")


def set_metadata(folder, stop_flag):
    for file in os.listdir(folder):
        if stop_flag.is_set():
            raise Exception("Stopped")
        if file.endswith('.mp3'):
            path = os.path.join(folder, file)
            name = file.replace('.mp3', '')
            parts = name.split(' - ', 1)
            artist = format_artists_for_metadata(parts[0]) if len(parts) > 1 else "Unknown"
            title = parts[1].strip() if len(parts) > 1 else name
            temp_path = path + '.temp.mp3'
            cmd = [
                'ffmpeg', '-y', '-i', path,
                '-metadata', f'artist={artist}',
                '-metadata', f'title={title}',
                '-c:a', 'copy',
                temp_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                os.remove(path)
                os.rename(temp_path, path)
            else:
                raise Exception(f"Metadata failed: {result.stderr}")


def renumber_files(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.mp3')]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    num_files = len(files)
    pad = 3 if num_files >= 99 else 2
    temp_map = {}
    for i, file in enumerate(files):
        temp_name = f"temp_{i:05d}.mp3"
        os.rename(os.path.join(folder, file), os.path.join(folder, temp_name))
        temp_map[temp_name] = file.replace('.mp3', '')
    for i, temp_name in enumerate(sorted(temp_map.keys(), key=lambda k: int(k.split('_')[1].split('.')[0]))):
        name = temp_map[temp_name]
        new_name = f"{i+1:0{pad}d} - {name}.mp3"
        os.rename(os.path.join(folder, temp_name), os.path.join(folder, new_name))

