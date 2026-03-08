"""Tiny orchestration tests for main.py."""

import main


def test_mp3_mode_routes_to_mp3_pipeline(tmp_path, monkeypatch, capsys):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    (processed_dir / "track.mp3").write_bytes(b"x")
    calls = []

    def fake_mp3_pipeline(folder, logger, stop_flag, accepted_duration_sec):
        calls.append(("mp3", accepted_duration_sec))
        return 123.45

    monkeypatch.setattr(main, "run_mp3_pipeline", fake_mp3_pipeline)
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--mode", "mp3", "--processed-dir", str(processed_dir),
         "--accepted-duration-sec", "3600"],
    )

    main.main()

    assert calls == [("mp3", 3600.0)]
    assert "123.45 MB" in capsys.readouterr().out


def test_audio_mode_routes_to_audio_pipeline(tmp_path, monkeypatch, capsys):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    (processed_dir / "track.mp3").write_bytes(b"x")
    calls = []

    def fake_audio_pipeline(folder, logger, stop_flag):
        calls.append("audio")
        return 67.89

    monkeypatch.setattr(main, "run_audio_cd_pipeline", fake_audio_pipeline)
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--mode", "audio", "--processed-dir", str(processed_dir)],
    )

    main.main()

    assert calls == ["audio"]
    assert "67.89 MB" in capsys.readouterr().out
