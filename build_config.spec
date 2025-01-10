# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 主程序
a = Analysis(
    ['main.py'],
    pathex=['D:\\works\\ddns_manager'],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=[
        'win32timezone',
        'cryptography',
        'tencentcloud.common',
        'tencentcloud.dnspod.v20210323'
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

# 服务程序
b = Analysis(
    ['service/ddns_service.py'],
    pathex=['D:\\works\\ddns_manager'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32timezone',
        'servicemanager',
        'win32serviceutil',
        'win32service'
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

pyz_a = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
pyz_b = PYZ(b.pure, b.zipped_data, cipher=block_cipher)

# 主程序exe
exe_a = EXE(
    pyz_a,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ddns_manager',
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
    icon='resources/icon.ico'
)

# 服务程序exe
exe_b = EXE(
    pyz_b,
    b.scripts,
    b.binaries,
    b.zipfiles,
    b.datas,
    [],
    name='ddns_service',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'
)
