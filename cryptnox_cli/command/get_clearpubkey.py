# -*- coding: utf-8 -*-
"""
Module containing command for getting clear public key from the card
"""
import cryptnox_sdk_py
from argparse import Namespace

from .command import Command
from .helper.security import check


class GetClearpubkey(Command):
    """
    Command to get the clear public key from the card (without PIN or secure channel)
    """
    _name = "get_clearpubkey"

    def _resolve_key_type(self, key_type_value):
        try:
            if isinstance(key_type_value, str):
                return cryptnox_sdk_py.KeyType[key_type_value.upper()]
            return key_type_value
        except Exception as error:
            raise ValueError(f"Invalid key type: {key_type_value}") from error

    def _print_pubkey_info(self, key_type, compressed, pubkey_bytes):
        pubkey_hex = pubkey_bytes.hex()
        print("\nClear Public Key Retrieved:")
        print(f"Key Type: {key_type.name}")
        print(f"Format: {'Compressed' if compressed else 'Uncompressed'}")
        print(f"Length: {len(pubkey_bytes)} bytes")
        print(f"Public Key: {pubkey_hex}")

        if len(pubkey_bytes) == 33:
            print("Format: Compressed (33 bytes)")
            prefix = pubkey_bytes[0]
            parity = 'even' if prefix == 0x02 else 'odd'
            print(f"Prefix: 0x{prefix:02x} ({parity} Y-coordinate)")
        elif len(pubkey_bytes) == 65:
            print("Format: Uncompressed (65 bytes)")
        elif len(pubkey_bytes) == 32:
            print("Format: 32-byte public key data")

    def _execute(self, card) -> int:
        """
        Execute the get_clearpubkey command to get clear public key from the card

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

            # Get path from command line arguments if provided
            path = getattr(self.data, 'path', '')

            # Get compression setting
            compressed = getattr(self.data, 'compressed', True)
            if hasattr(self.data, 'uncompressed') and self.data.uncompressed:
                compressed = False

            print("Getting clear public key from card...")
            print(f"Key type: {key_type}")
            print(f"Path: {path if path else cryptnox_sdk_py.Derivation.CURRENT_KEY}")
            print(f"Compressed: {compressed}")

            # Enable clear pubkey reading capability if PUK provided
            if puk:
                print("Enabling clear pubkey reading capability...")
                try:
                    card.set_clearpubkey(True, puk)
                    print("Clear pubkey reading capability enabled")
                except cryptnox_sdk_py.exceptions.PukException as error:
                    print(f"Error: Invalid PUK code - {error}")
                    return -1
                except Exception as error:
                    print(f"Error enabling clear pubkey capability: {error}")
                    return -1

            # Calculate derivation parameter
            # For K1: derivation = 0x00 (current key)
            # For R1: derivation = 0x10 (current key R1)
            derivation = 0x00 if key_type == cryptnox_sdk_py.KeyType.K1 else 0x10

            try:
                # Get clear public key using get_public_key_clear
                if hasattr(card, 'get_public_key_clear'):
                    try:
                        if path:
                            card.derive(key_type, path)
                        else:
                            card.derive(key_type, "m/44'/0'/0'")
                    except Exception:
                        # Best-effort derivation; clear pubkey read below handles failures
                        pass
                    pubkey_bytes = card.get_public_key_clear(derivation, path, compressed)
                    self._print_pubkey_info(key_type, compressed, pubkey_bytes)
                else:
                    print("Error: Card does not support clear pubkey reading")
                    print("This feature requires a compatible card firmware version")
                    return -1

            except cryptnox_sdk_py.exceptions.ReadPublicKeyException as error:
                if "6A88" in str(error):
                    print("Error: Clear pubkey reading capability not enabled")
                    print("Please enable it first with: cryptnox get_clearpubkey --puk 'your_puk'")
                elif "6985" in str(error):
                    print("Error: No seed loaded or PIN not verified")
                    print("Please load a seed first: cryptnox seed")
                elif "uncompressed" in str(error):
                    print("Error: Cannot get uncompressed public key")
                    print("The card does not return uncompressed keys in clear channel mode.")
                    print("Use --compressed flag to get a compressed public key instead.")
                else:
                    print(f"Error reading clear public key: {error}")
                return -1
            except Exception as error:
                print(f"Unexpected error: {error}")
                return -1

            return 0

        except cryptnox_sdk_py.exceptions.SeedException:
            print("Error: No seed exists on the card. Please initialize the card first.")
            print("Run: cryptnox init")
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
        Add command line options for the get_clearpubkey command

        :param subparsers: Argument parser subparsers
        """
        clearpubkey_parser = subparsers.add_parser(
            "get_clearpubkey",
            help="Get clear public key from the card (without PIN or secure channel)"
        )

        clearpubkey_parser.add_argument(
            "--key-type",
            choices=['K1', 'R1'],
            default='K1',
            help="Key type to use (default: K1)"
        )

        clearpubkey_parser.add_argument(
            "--puk",
            type=str,
            default='',
            help="PUK code to enable clear pubkey reading capability (required for first use)"
        )

        clearpubkey_parser.add_argument(
            "--path",
            type=str,
            default='',
            help="BIP path for key derivation (e.g., m/44'/0'/0'). Leave empty for current key."
        )

        clearpubkey_parser.add_argument(
            "--compressed",
            action='store_true',
            default=True,
            help="Return compressed public key format (default: True)"
        )

        clearpubkey_parser.add_argument(
            "--uncompressed",
            action='store_true',
            help="Return uncompressed public key format"
        )
