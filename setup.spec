# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Find lazy_import VERSION file
import lazy_import
lazy_import_version = os.path.join(os.path.dirname(lazy_import.__file__), 'VERSION')

a = Analysis(
    ['cryptnox_cli\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Only include non-Python data files
        ('cryptnox_cli\\contract_abi\\*.json', 'cryptnox_cli\\contract_abi'),
        ('cryptnox_cli\\lib\\cryptos\\english.txt', 'cryptnox_cli\\lib\\cryptos'),
        (lazy_import_version, 'lazy_import')
    ],
    hiddenimports=[
        'lazy_import',
        'six',
        'winsdk',
        'winsdk.windows',
        'winsdk.windows.security.credentials',
        'winsdk.windows.security.cryptography',
        'nfc',
        'smartcard',
        'multiprocessing',
        'tabulate',
        'coincurve',
        'eth_keys',
        'requests',
        'urllib3',
        'websockets',
        'aiohttp',
        'botocore',
        'awscrt',
        # Dynamically imported command modules
        'cryptnox_cli.command.btc',
        'cryptnox_cli.command.card_configuration',
        'cryptnox_cli.command.change_pin',
        'cryptnox_cli.command.change_puk',
        'cryptnox_cli.command.config',
        'cryptnox_cli.command.eth',
        'cryptnox_cli.command.history',
        'cryptnox_cli.command.info',
        'cryptnox_cli.command.initialize',
        'cryptnox_cli.command.seed',
        'cryptnox_cli.command.cards',
        'cryptnox_cli.command.server',
        'cryptnox_cli.command.reset',
        'cryptnox_cli.command.unlock_pin',
        'cryptnox_cli.command.user_key',
        'cryptnox_cli.command.transfer',
        'cryptnox_cli.command.get_xpub',
        'cryptnox_cli.command.get_clearpubkey',
        'cryptnox_cli.command.decrypt',
        # Command submodules (imported by initialize and info)
        'cryptnox_cli.command.card',
        'cryptnox_cli.command.card.info',
        'cryptnox_cli.command.card.initialize',
        'cryptnox_cli.command.erc_token',
        'cryptnox_cli.command.erc_token.contract',
        'cryptnox_cli.command.erc_token.info',
        'cryptnox_cli.command.erc_token.initialize',
        # Dynamically imported user_keys submodules
        'cryptnox_cli.command.user_keys.aws_kms',
        'cryptnox_cli.command.user_keys.hello',
        'cryptnox_cli.command.user_keys.piv',
        # lib.cryptos modules (dynamically imported)
        'cryptnox_cli.lib.cryptos',
        'cryptnox_cli.lib.cryptos.blocks',
        'cryptnox_cli.lib.cryptos.composite',
        'cryptnox_cli.lib.cryptos.deterministic',
        'cryptnox_cli.lib.cryptos.main',
        'cryptnox_cli.lib.cryptos.mnemonic',
        'cryptnox_cli.lib.cryptos.specials',
        'cryptnox_cli.lib.cryptos.stealth',
        'cryptnox_cli.lib.cryptos.transaction',
        'cryptnox_cli.lib.cryptos.coins',
        'cryptnox_cli.lib.cryptos.coins.base',
        'cryptnox_cli.lib.cryptos.coins.bitcoin',
        'cryptnox_cli.lib.cryptos.keystore',
        'cryptnox_cli.lib.cryptos.wallet',
        'cryptnox_cli.lib.cryptos.wallet_utils',
        'cryptnox_cli.lib.cryptos.pbkdf2',
        'cryptnox_cli.lib.cryptos.ripemd',
        'cryptnox_cli.lib.cryptos.segwit_addr',
        # wallet modules (dynamically imported)
        'cryptnox_cli.wallet',
        'cryptnox_cli.wallet.btc',
        'cryptnox_cli.wallet.eth',
        'cryptnox_cli.wallet.eth.api',
        'cryptnox_cli.wallet.eth.endpoint',
        'cryptnox_cli.wallet.validators'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['build'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CryptnoxCLI-1.0.2',
    icon='cryptnox.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=False,
)
