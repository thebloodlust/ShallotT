# -*- mode: python ; coding: utf-8 -*-
# ShallotT PyInstaller spec — one-folder mode (AV-friendly)
# UPX disabled to avoid false positives.
# For single-file mode, use: python build_exe.py --onefile

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
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
    name='ShallotT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX disabled — reduces antivirus false positives
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # Add icon path here in the future, e.g.: icon='icons/shallott.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,            # UPX disabled — reduces antivirus false positives
    upx_exclude=[],
    name='ShallotT',
)
