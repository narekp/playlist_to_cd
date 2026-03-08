"""Unit tests for core.ffmpeg_utils. Subprocess calls are mocked."""

import shutil
import subprocess
import time
from pathlib import Path

import pytest

from core.ffmpeg_utils import (
    convert_to_bitrate,
    estimate_required_bitrate,
    get_total_size,
    renumber_files,
    set_metadata,
    verify_duration,
)


class TestGetTotalSize:
    def test_empty_folder(self, tmp_path):
        assert get_total_size(tmp_path) == 0.0

    def test_folder_with_mp3_files(self, tmp_path):
        (tmp_path / "a.mp3").write_bytes(b"x" * 1024)
        (tmp_path / "b.mp3").write_bytes(b"y" * 2048)
        (tmp_path / "other.txt").write_bytes(b"z" * 100)

        size_mb = get_total_size(tmp_path)

        assert size_mb == pytest.approx((1024 + 2048) / (1024 * 1024), rel=1e-6)


class TestEstimateRequiredBitrate:
    def test_zero_duration(self):
        assert estimate_required_bitrate(0) == 320

    def test_negative_duration(self):
        assert estimate_required_bitrate(-100) == 320

    def test_normal_case(self):
        assert 100 <= estimate_required_bitrate(3600, target_mb=699) <= 2000

    def test_boundary_small_duration(self):
        assert estimate_required_bitrate(1, target_mb=699) >= 320


class TestRenumberFiles:
    def test_empty_folder(self, tmp_path):
        renumber_files(tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_one_file(self, tmp_path):
        (tmp_path / "x.mp3").write_bytes(b"a")

        renumber_files(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.mp3")) == ["01 - x.mp3"]

    def test_many_files_pad_two(self, tmp_path):
        for i in range(5):
            (tmp_path / f"track{i}.mp3").write_bytes(b"x")

        renumber_files(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.mp3")) == [
            "01 - track0.mp3",
            "02 - track1.mp3",
            "03 - track2.mp3",
            "04 - track3.mp3",
            "05 - track4.mp3",
        ]

    def test_pad_three_for_99_plus(self, tmp_path):
        for i in range(99):
            (tmp_path / f"t{i}.mp3").write_bytes(b"x")

        renumber_files(tmp_path)

        names = sorted(f.name for f in tmp_path.glob("*.mp3"))
        assert names[0] == "001 - t0.mp3"
        assert names[-1] == "099 - t98.mp3"

    def test_ordering_by_mtime(self, tmp_path):
        (tmp_path / "first.mp3").write_bytes(b"a")
        time.sleep(0.01)
        (tmp_path / "second.mp3").write_bytes(b"b")

        renumber_files(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.mp3")) == [
            "01 - first.mp3",
            "02 - second.mp3",
        ]


class TestVerifyDuration:
    def test_stop_flag_raises(self, tmp_path, stop_flag):
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            verify_duration(str(tmp_path / "x.mp3"), "180000", stop_flag)

    def test_within_tolerance_returns_true(self, tmp_path, monkeypatch, stop_flag):
        file_path = str(tmp_path / "f.mp3")
        Path(file_path).write_bytes(b"x")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="180.0", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert verify_duration(file_path, "180000", stop_flag) is True
        assert len(calls) == 1
        assert calls[0][0] == "ffprobe"
        assert calls[0][-1] == file_path

    def test_outside_tolerance_returns_false(self, tmp_path, monkeypatch, stop_flag):
        file_path = str(tmp_path / "f.mp3")
        Path(file_path).write_bytes(b"x")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="300.0", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert verify_duration(file_path, "180000", stop_flag) is False

    def test_missing_expected_duration_uses_15_min_cutoff(self, tmp_path, monkeypatch, stop_flag):
        file_path = str(tmp_path / "f.mp3")
        Path(file_path).write_bytes(b"x")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="901.0", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert verify_duration(file_path, "", stop_flag) is False

    def test_ffprobe_failure_returns_false(self, tmp_path, monkeypatch, stop_flag):
        file_path = str(tmp_path / "f.mp3")
        Path(file_path).write_bytes(b"x")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert verify_duration(file_path, "180000", stop_flag) is False


class TestConvertToBitrate:
    def test_stop_flag_raises(self, tmp_path, stop_flag):
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            convert_to_bitrate(tmp_path, tmp_path / "out", 128, stop_flag)

    def test_converts_each_mp3_to_output_folder(self, tmp_path, monkeypatch, stop_flag):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.mp3").write_bytes(b"content_a")
        (src / "b.mp3").write_bytes(b"content_b")
        out = tmp_path / "out"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            shutil.copy2(cmd[cmd.index("-i") + 1], cmd[-1])
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        convert_to_bitrate(src, out, 128, stop_flag)

        assert (out / "a.mp3").exists()
        assert (out / "b.mp3").exists()
        assert len(calls) == 2
        for cmd in calls:
            assert cmd[0] == "ffmpeg"
            assert "128k" in cmd


class TestSetMetadata:
    def test_stop_flag_raises(self, tmp_path, stop_flag):
        (tmp_path / "Artist - Title.mp3").write_bytes(b"x")
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            set_metadata(tmp_path, stop_flag)

    def test_extracts_artist_and_title_from_filename(self, tmp_path, monkeypatch, stop_flag):
        input_file = tmp_path / "Artist1, Artist2 - Title.mp3"
        input_file.write_bytes(b"content")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            Path(cmd[-1]).write_bytes(Path(cmd[cmd.index("-i") + 1]).read_bytes())
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        set_metadata(tmp_path, stop_flag)

        assert input_file.exists()
        assert input_file.read_bytes() == b"content"
        assert len(calls) == 1
        cmd = calls[0]
        assert cmd[0] == "ffmpeg"
        assert "artist=Artist1, Artist2" in cmd
        assert "title=Title" in cmd
