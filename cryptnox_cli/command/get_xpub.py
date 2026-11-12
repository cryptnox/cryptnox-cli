# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for getting extended public key (xpub) from the card
"""
import binascii
import hashlib
import cryptnox_sdk_py
from argparse import Namespace

from .command import Command
from .helper.security import check

try:
    import base58
except ImportError:
    base58 = None

KNOWN_VERSIONS = {
    b"\x04\x88\xB2\x1E": "xpub",  # mainnet
    b"\x04\x35\x87\xCF": "tpub",  # testnet
    b"\x04\x9D\x7C\xB2": "ypub",  # p2wpkh-p2sh
    b"\x04\xB2\x47\x46": "zpub",  # p2wpkh
    b"\x04\x4A\x52\x62": "upub",  # testnet p2wpkh-p2sh
    b"\x04\x5F\x1C\xF6": "vpub",  # testnet p2wpkh
}


def _ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD-160 hash"""
    try:
        return hashlib.new('ripemd160', data).digest()
    except ValueError:
        try:
            from cryptnox_sdk_py.cryptos.ripemd import ripemd160
            return ripemd160(data)
        except ImportError:
            raise RuntimeError("RIPEMD-160 not available")


def _double_sha256(data: bytes) -> bytes:
    """Compute double SHA256 hash"""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def extended_to_xpub(hex_str: str):
    """
    Convert 106-byte Cryptnox extended key format to standard Base58 xpub.
    Cryptnox format (106 bytes):
    - version: 4 bytes
    - depth: 1 byte
    - parent_fp32: 32 bytes (SHA256 of parent pubkey)
    - child_number: 4 bytes
    - chain_code: 32 bytes
    - key: 33 bytes (compressed pubkey)
    Returns: (success: bool, message: str, xpub: str or None)
    """
    if base58 is None:
        return False, "base58 module not installed", None

    try:
        raw = binascii.unhexlify(hex_str.strip().replace(" ", ""))
    except Exception as e:
        return False, f"Invalid hex: {e}", None

    if len(raw) != 106:
        return False, f"Expected 106 bytes, got {len(raw)}", None

    # Parse fields
    version = raw[0:4]
    depth = raw[4:5]
    parent_fp32 = raw[5:37]
    child_number = raw[37:41]
    chain_code = raw[41:73]
    key = raw[73:106]

    # Validate version
    if version not in KNOWN_VERSIONS:
        return False, f"Unknown version: {version.hex()}", None

    # Validate key is compressed
    if len(key) != 33 or key[0] not in (0x02, 0x03):
        return False, "Invalid compressed public key", None

    # Compute BIP32 4-byte parent fingerprint from 32-byte SHA256
    parent_fp4 = _ripemd160(parent_fp32)[:4]

    # Build canonical 78-byte BIP32 extended key
    bip32_payload = version + depth + parent_fp4 + child_number + chain_code + key

    # Base58Check encode
    checksum = _double_sha256(bip32_payload)[:4]
    xpub = base58.b58encode(bip32_payload + checksum).decode()

    return True, KNOWN_VERSIONS[version], xpub


class GetXpub(Command):
    """
    Command to get the extended public key (get_xpub) from the card
    """
    _name = "get_xpub"

    def _resolve_key_type(self, key_type_value):
        try:
            if isinstance(key_type_value, str):
                return cryptnox_sdk_py.KeyType[key_type_value.upper()]
            return key_type_value
        except Exception as error:
            raise ValueError(f"Invalid key type: {key_type_value}") from error

    def _print_xpub(self, key_type, xpub_hex):
        """
        Print the extended public key in Base58 format

        :param key_type: The key type (K1 or R1)
        :param xpub_hex: The extended public key in hex format from the card (106 bytes)
        """
        print("K1 Extended Public Key" if key_type == cryptnox_sdk_py.KeyType.K1 else "Extended Public Key")

        # Convert Cryptnox 106-byte format to standard Base58 xpub
        success, message, xpub = extended_to_xpub(xpub_hex)

        if success:
            print(f"{xpub}")
            print(f"\n({message}, depth level {ord(binascii.unhexlify(xpub_hex)[4:5])})")
        else:
            # Fallback to hex if conversion fails
            print(f"Warning: {message}")
            print(f"Raw hex: {xpub_hex}")

    def _execute(self, card) -> int:
        """
        Execute the xpub command to get extended public key from the card

        :param card: The card instance
        :return: 0 if successful, other number indicating an issue
        :rtype: int
        """
        check(card)

        try:
            # Get key type from command line arguments, default to K1
            key_type = self._resolve_key_type(getattr(self.data, 'key_type', 'K1'))

            # Get PUK from command line arguments if provided
            puk = getattr(self.data, 'puk', '')

            if key_type == cryptnox_sdk_py.KeyType.R1:
                print("Cannot get extended public key for R1 key.")
            else:
                # For K1 keys, use clear export for xpub (if enabled or PUK provided)
                try:
                    print("Getting extended public key for K1 key...")
                    if puk:
                        print("Enabling public key export capability...")
                    xpubkey = card.get_public_key_extended(key_type=key_type, puk=puk)
                    print("")
                    self._print_xpub(key_type, xpubkey)
                except Exception as error:
                    print(f"Error getting K1 public key: {error}")
                    return -1

            return 0

        except cryptnox_sdk_py.exceptions.SeedException:
            print("Error: No seed exists on the card. Please initialize the card first.")
            return -1
        except cryptnox_sdk_py.exceptions.ReadPublicKeyException as e:
            print(f"Error reading public key: {e}")
            return -1
        except Exception as error:
            print(f"Unexpected error: {error}")
            return -1

    @classmethod
    def meets_condition(cls, data: Namespace) -> bool:
        """
        Check if this command should handle the given arguments

        :param data: Command line arguments
        :return: True if this command should handle the arguments
        :rtype: bool
        """
        return hasattr(data, 'command') and data.command == cls._name

    @staticmethod
    def add_options(subparsers) -> None:
        """
        Add command line options for the xpub command

        :param subparsers: Argument parser subparsers
        """
        subparsers.add_parser(
            "get_xpub",
            help="Get public key using clear pubkey reading (P1=0x01) capability"
        )
