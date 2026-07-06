# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
project_dir = Path.cwd()
package_dir = project_dir / "watchless_app"
icon_file = project_dir / "App Icons" / "WatchLess.icns"
entitlements_file = project_dir / "entitlements.plist"

datas = [
    (str(package_dir / "templates"), "watchless_app/templates"),
    (str(package_dir / "static"), "watchless_app/static"),
    (str(package_dir / "local_voice_server.py"), "watchless_app"),
]

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WatchLess",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(entitlements_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WatchLess",
)

app = BUNDLE(
    coll,
    name="WatchLess.app",
    icon=str(icon_file),
    bundle_identifier="com.local.watchless",
    info_plist={
        "CFBundleName": "WatchLess",
        "CFBundleDisplayName": "WatchLess",
        "NSHighResolutionCapable": "True",
    },
)
