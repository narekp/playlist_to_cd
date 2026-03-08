# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for playlist_to_cd macOS app (onedir + .app bundle).
Run from project root: ./packaging/build_macos.sh
"""
import os
import sys

block_cipher = None

# Project root (parent of packaging/)
spec_dir = os.path.dirname(os.path.abspath(SPEC))
project_root = os.path.dirname(spec_dir)

# Bundle binaries if they exist in packaging/bin/
datas = []
bin_dir = os.path.join(project_root, "packaging", "bin")
for name in ["ffmpeg", "ffprobe", "yt-dlp"]:
    path = os.path.join(bin_dir, name)
    if os.path.exists(path):
        datas.append((path, "bin"))

a = Analysis(
    [os.path.join(project_root, "packaging", "launcher.py")],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="playlist_to_cd",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="playlist_to_cd",
)

# macOS .app bundle (only used when building on macOS)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Spotify Playlist to Disk Converter.app",
        icon=None,
        bundle_identifier="net.exportify.playlist_to_cd",
        version="0.1.0",
    )
