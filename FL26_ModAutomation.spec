# FL26_ModAutomation.spec
# Build command: pyinstaller FL26_ModAutomation.spec

block_cipher = None

a = Analysis(
    ['FL26_ModAutomation.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the config and player CSV alongside the exe
        ('FL26_ModAutomation.config.json', '.'),
        ('PlayerIds.csv', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='FL26_ModAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # uncomment and add icon.ico to use a custom icon
)
