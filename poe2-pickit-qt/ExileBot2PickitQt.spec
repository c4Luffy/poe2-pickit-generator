# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the PySide6 app. One-file, windowed (no console).
#
# Build:  pyinstaller ExileBot2PickitQt.spec --noconfirm
#
# Notes:
#   * pathex includes the repo root so `poe2_pickit_generator` is found and
#     analysed as a real module (its `requests` dependency comes along).
#   * src/styles (the QSS template + theme JSON) is read at runtime by path, so
#     it must be bundled as data; theme_manager resolves it from _MEIPASS when
#     frozen.
#   * customtkinter/PIL/tkinter (the OLD app's GUI stack) are excluded — the Qt
#     app doesn't use them — to keep the binary smaller.
import os

here = SPECPATH
repo_root = os.path.dirname(here)

a = Analysis(
    ['main.py'],
    pathex=[here, repo_root],
    binaries=[],
    datas=[(os.path.join(here, 'src', 'styles'), os.path.join('src', 'styles'))],
    hiddenimports=[
        'poe2_pickit_generator',
        'requests', 'certifi', 'charset_normalizer', 'urllib3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'PIL', 'tkinter', 'matplotlib', 'numpy', 'scipy'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ExileBot2PickitQt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
