"""Tests for modes.mp3_cd."""

from pathlib import Path

import pytest

from modes.mp3_cd import process_mp3_folder, run_mp3_pipeline


class TestProcessMp3Folder:
    def test_size_under_699_skips_bitrate_reduction(self, tmp_path, monkeypatch, log_queue, stop_flag):
        (tmp_path / "Artist - Title.mp3").write_bytes(b"x")
        bitrate_attempted = []
        metadata_called = []
        renumber_called = []

        monkeypatch.setattr("modes.mp3_cd.get_total_size", lambda folder: 100.0)
        monkeypatch.setattr(
            "modes.mp3_cd.convert_to_bitrate",
            lambda folder, temp, br, flag: bitrate_attempted.append(br),
        )
        monkeypatch.setattr(
            "modes.mp3_cd.set_metadata",
            lambda folder, flag: metadata_called.append(True),
        )
        monkeypatch.setattr(
            "modes.mp3_cd.renumber_files",
            lambda folder: renumber_called.append(True),
        )

        process_mp3_folder(str(tmp_path), log_queue, stop_flag, 320)

        assert bitrate_attempted == []
        assert len(metadata_called) == 1
        assert len(renumber_called) == 1

    def test_size_over_699_tries_bitrates_until_one_fits(self, tmp_path, monkeypatch, log_queue, stop_flag):
        (tmp_path / "01 - Artist - Title.mp3").write_bytes(b"original")
        bitrates_tried = []

        def fake_get_total_size(folder):
            folder = str(folder)
            if folder == str(tmp_path):
                files = sorted(p.name for p in tmp_path.glob("*.mp3"))
                if files == ["01 - Artist - Title.mp3"]:
                    return 800.0
                return 650.0
            if folder.endswith("_temp_320"):
                return 750.0
            if folder.endswith("_temp_256"):
                return 650.0
            return 650.0

        def fake_convert_to_bitrate(folder, temp_folder, bitrate, flag):
            bitrates_tried.append(bitrate)
            temp_path = Path(temp_folder)
            temp_path.mkdir(exist_ok=True)
            (temp_path / f"converted-{bitrate}.mp3").write_bytes(b"x")

        monkeypatch.setattr("modes.mp3_cd.get_total_size", fake_get_total_size)
        monkeypatch.setattr("modes.mp3_cd.convert_to_bitrate", fake_convert_to_bitrate)
        monkeypatch.setattr("modes.mp3_cd.set_metadata", lambda folder, flag: None)
        monkeypatch.setattr("modes.mp3_cd.renumber_files", lambda folder: None)

        process_mp3_folder(str(tmp_path), log_queue, stop_flag, 320)

        assert bitrates_tried == [320, 256]
        assert sorted(p.name for p in tmp_path.glob("*.mp3")) == ["converted-256.mp3"]
        assert not Path(str(tmp_path) + "_temp_320").exists()
        assert not Path(str(tmp_path) + "_temp_256").exists()

    def test_stop_flag_raises(self, tmp_path, log_queue, stop_flag):
        (tmp_path / "a.mp3").write_bytes(b"x")
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            process_mp3_folder(str(tmp_path), log_queue, stop_flag, 320)


class TestRunMp3Pipeline:
    def test_selects_start_bitrate_and_returns_final_size(self, tmp_path, monkeypatch, log_queue, stop_flag):
        captured_bitrate = []

        monkeypatch.setattr("modes.mp3_cd.estimate_required_bitrate", lambda seconds: 210)
        monkeypatch.setattr(
            "modes.mp3_cd.process_mp3_folder",
            lambda folder, queue, flag, start_bitrate: captured_bitrate.append(start_bitrate),
        )
        monkeypatch.setattr("modes.mp3_cd.get_total_size", lambda folder: 123.4)

        final_size = run_mp3_pipeline(str(tmp_path), log_queue, stop_flag, 3600)

        assert captured_bitrate == [192]
        assert final_size == 123.4
