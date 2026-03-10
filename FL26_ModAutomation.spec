# FL26_ModAutomation.spec
# Build command: pyinstaller FL26_ModAutomation.spec

block_cipher = None

a = Analysis(
    ['FL26_ModAutomation.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Config and player CSV
        ('FL26_ModAutomation.config.json', '.'),
        ('PlayerIds.csv', '.'),
        # PowerShell scripts
        ('Run-FL26-ModAutomation.ps1',   '.'),
        ('Assign-GripSox-Single.ps1',    '.'),
        ('Assign-GripSox-Brands.ps1',    '.'),
        ('Assign-Socks.ps1',             '.'),
        ('Assign-Pants.ps1',             '.'),
        ('Assign-Shirt.ps1',             '.'),
        ('Assign-Gloves.ps1',            '.'),
        ('Assign-Sleeve.ps1',            '.'),
        ('Assign-Wristtaping.ps1',       '.'),
        ('Assign-Handtape.ps1',          '.'),
        ('Validate-Assignments.ps1',     '.'),
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
    name='FL26 Mod Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',    # uncomment and add icon.ico to use a custom icon
)
