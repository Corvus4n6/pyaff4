# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for building the aff4 CLI tool as a standalone binary.
# Bundles the pyaff4 package and all dependencies into a single executable.
#
# Usage:
#   pyinstaller aff4.spec
#
# Output: dist/aff4  (Linux/macOS)  or  dist/aff4.exe  (Windows)

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect all data files and submodules for packages that use dynamic imports
rdflib_datas, rdflib_binaries, rdflib_hiddenimports = collect_all('rdflib')
snappy_datas, snappy_binaries, snappy_hiddenimports = collect_all('snappy')
lz4_datas, lz4_binaries, lz4_hiddenimports = collect_all('lz4')
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all('nacl')
crypto_datas, crypto_binaries, crypto_hiddenimports = collect_all('Crypto')
pyaff4_datas, pyaff4_binaries, pyaff4_hiddenimports = collect_all('pyaff4')
fc_datas, fc_binaries, fc_hiddenimports = collect_all('fastchunking')

a = Analysis(
    ['aff4.py'],
    pathex=['.'],
    binaries=(
        snappy_binaries +
        lz4_binaries +
        nacl_binaries +
        crypto_binaries +
        pyaff4_binaries +
        fc_binaries
    ),
    datas=(
        rdflib_datas +
        snappy_datas +
        lz4_datas +
        nacl_datas +
        crypto_datas +
        pyaff4_datas +
        fc_datas
    ),
    hiddenimports=(
        rdflib_hiddenimports +
        snappy_hiddenimports +
        lz4_hiddenimports +
        nacl_hiddenimports +
        crypto_hiddenimports +
        pyaff4_hiddenimports +
        [
            # rdflib plugins registered via entry points
            'rdflib.plugins.parsers.notation3',
            'rdflib.plugins.parsers.nquads',
            'rdflib.plugins.parsers.trig',
            'rdflib.plugins.parsers.turtle',
            'rdflib.plugins.serializers.turtle',
            'rdflib.plugins.serializers.n3',
            'rdflib.plugins.serializers.nquads',
            'rdflib.plugins.serializers.trig',
            # pyaff4 submodules
            'pyaff4.aff4',
            'pyaff4.aff4_image',
            'pyaff4.aff4_map',
            'pyaff4.aff4_metadata',
            'pyaff4.aff4_directory',
            'pyaff4.container',
            'pyaff4.data_store',
            'pyaff4.escaping',
            'pyaff4.hashes',
            'pyaff4.hexdump',
            'pyaff4.layout',
            'pyaff4.lexicon',
            'pyaff4.linear_hasher',
            'pyaff4.logical',
            'pyaff4.rdfvalue',
            'pyaff4.registry',
            'pyaff4.utils',
            'pyaff4.version',
            'pyaff4.zip',
            # standard library modules that may be missed
            'email.mime.text',
            'email.mime.multipart',
            'encodings.utf_8',
            'encodings.ascii',
            'encodings.latin_1',
            # other deps
            'intervaltree',
            'yaml',
            'tzlocal',
            'dateutil',
            'html5lib',
            'passlib',
            'expiringdict',
            'fastchunking',
            'fastchunking._rabinkarprh',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude large unused packages
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'wx',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
    ],
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
    [],
    name='aff4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2' if sys.platform == 'darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
)
