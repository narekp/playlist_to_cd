"""Tests for modes.audio_cd. Subprocess calls are mocked."""

import queue
import subprocess
from pathlib import Path

import pytest

from modes.audio_cd import convert_to_wav, renumber_wavs, run_audio_cd_pipeline


class TestRenumberWavs:
    def test_empty_folder(self, tmp_path):
        renumber_wavs(tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_one_file(self, tmp_path):
        (tmp_path / "x.wav").write_bytes(b"a")

        renumber_wavs(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.wav")) == ["01.wav"]

    def test_pad_two_for_under_100(self, tmp_path):
        for i in range(5):
            (tmp_path / f"track{i}.wav").write_bytes(b"x")

        renumber_wavs(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.wav")) == [
            "01.wav",
            "02.wav",
            "03.wav",
            "04.wav",
            "05.wav",
        ]

    def test_pad_three_for_100_plus(self, tmp_path):
        for i in range(100):
            (tmp_path / f"t{i}.wav").write_bytes(b"x")

        renumber_wavs(tmp_path)

        names = sorted(f.name for f in tmp_path.glob("*.wav"))
        assert names[0] == "001.wav"
        assert names[-1] == "100.wav"

    def test_no_op_when_already_numbered(self, tmp_path):
        (tmp_path / "01.wav").write_bytes(b"a")

        renumber_wavs(tmp_path)

        assert sorted(f.name for f in tmp_path.glob("*.wav")) == ["01.wav"]

    def test_ignores_non_wav(self, tmp_path):
        (tmp_path / "a.mp3").write_bytes(b"x")
        (tmp_path / "b.wav").write_bytes(b"y")

        renumber_wavs(tmp_path)

        assert (tmp_path / "a.mp3").exists()
        assert sorted(f.name for f in tmp_path.glob("*.wav")) == ["01.wav"]


class TestConvertToWav:
    def test_stop_flag_raises(self, tmp_path, stop_flag):
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            convert_to_wav(str(tmp_path / "x.mp3"), str(tmp_path / "out.wav"), stop_flag)

    def test_calls_ffmpeg_and_produces_output(self, tmp_path, monkeypatch, stop_flag):
        input_file = tmp_path / "in.mp3"
        input_file.write_bytes(b"x")
        output_file = tmp_path / "out.wav"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            Path(cmd[-1]).write_bytes(b"wav")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        convert_to_wav(str(input_file), str(output_file), stop_flag)

        assert output_file.read_bytes() == b"wav"
        assert len(calls) == 1
        cmd = calls[0]
        assert cmd[0] == "ffmpeg"
        assert str(input_file) in cmd
        assert str(output_file) in cmd


class TestRunAudioCdPipeline:
    def test_produces_numbered_wavs_in_sorted_mp3_order(self, tmp_path, monkeypatch, stop_flag):
        (tmp_path / "beta.mp3").write_bytes(b"x")
        (tmp_path / "alpha.mp3").write_bytes(b"y")
        (tmp_path / "ignore.txt").write_text("skip")
        log_queue = queue.Queue()

        def fake_convert(mp3_path, wav_path, received_stop_flag):
            Path(wav_path).write_bytes(b"wavdata")

        monkeypatch.setattr("modes.audio_cd.convert_to_wav", fake_convert)

        total_mb = run_audio_cd_pipeline(str(tmp_path), log_queue, stop_flag)

        audio_dir = tmp_path / "audio_cd_ready"
        assert sorted(f.name for f in audio_dir.glob("*.wav")) == [
            "01 - alpha.wav",
            "02 - beta.wav",
        ]
        assert total_mb == pytest.approx((2 * len(b"wavdata")) / (1024 * 1024))
        assert log_queue.qsize() == 2

    def test_stop_flag_raises(self, tmp_path, log_queue, stop_flag):
        (tmp_path / "a.mp3").write_bytes(b"x")
        stop_flag.set()

        with pytest.raises(Exception, match="Stopped"):
            run_audio_cd_pipeline(str(tmp_path), log_queue, stop_flag)
