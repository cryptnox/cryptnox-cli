# -*- coding: utf-8 -*-
"""
XRP address derivation and balance lookup from secp256k1 public key.

XRP uses the same secp256k1 curve as Bitcoin. The address is derived by:
1. SHA-256 hash of the compressed public key
2. RIPEMD-160 of the SHA-256 result (Account ID)
3. Base58Check encoding with version byte 0x00 using the XRP alphabet
"""
import hashlib

import base58
import requests

PATH = "m/44'/144'/0'/0/0"

# XRP uses a different Base58 alphabet than Bitcoin
XRP_ALPHABET = b'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz'

MAINNET_RPC = "https://s1.ripple.com:51234/"

# 1 XRP = 1 000 000 drops
_DROPS_PER_XRP = 1_000_000


def address(public_key_hex: str) -> str:
    """
    Derive an XRP classic address (r-address) from a compressed secp256k1 public key.

    :param str public_key_hex: Compressed public key as a hex string (33 bytes / 66 hex chars)
    :return: XRP address starting with 'r'
    :rtype: str
    """
    public_key_bytes = bytes.fromhex(public_key_hex)

    sha256_hash = hashlib.sha256(public_key_bytes).digest()

    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    account_id = ripemd160.digest()

    # Version byte 0x00 for XRP classic addresses
    return base58.b58encode_check(b'\x00' + account_id, alphabet=XRP_ALPHABET).decode()


def get_balance(xrp_address: str) -> float:
    """
    Return the XRP balance for *xrp_address* in XRP (not drops).

    Returns 0.0 for accounts that exist on-chain but have not yet been funded
    (actNotFound). Raises an exception for any other network or protocol error.

    :param str xrp_address: Classic r-address (e.g. 'rHb9CJA...')
    :return: Balance in XRP
    :rtype: float
    :raises requests.RequestException: On HTTP / connection failures
    :raises ValueError: On unexpected ledger error responses
    """
    payload = {
        "method": "account_info",
        "params": [{"account": xrp_address, "ledger_index": "current"}],
    }
    response = requests.post(MAINNET_RPC, json=payload, timeout=10)
    response.raise_for_status()

    result = response.json().get("result", {})

    # Account exists but has never been funded – treat as zero balance
    if result.get("error") == "actNotFound":
        return 0.0

    if result.get("status") == "error":
        raise ValueError(result.get("error_message", "XRP network error"))

    drops = int(result["account_data"]["Balance"])
    return drops / _DROPS_PER_XRP
