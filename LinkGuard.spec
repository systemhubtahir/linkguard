# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/assets/theme.json', 'assets'),
    ],
    hiddenimports=['customtkinter', 'pandas', 'requests'],
    hookspath=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LinkGuard',
    debug=False,
    strip=False,
    upx=True,
    console=False,         # No console window on launch
    icon='src/assets/icon.ico',
)

# macOS .app bundle
app = BUNDLE(
    exe,
    name='LinkGuard.app',
    icon='src/assets/icon.icns',
    bundle_identifier='com.linkguard.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)
