# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for decrypting data using ECIES
"""
try:
    import cryptnox_sdk_py
except ImportError:
    # Handle case where cryptnox_sdk_py is not available
    cryptnox_sdk_py = None

from argparse import Namespace

from .command import Command


class Decrypt(Command):
    """
    Command to decrypt data using ECIES (Elliptic Curve Integrated Encryption Scheme)
    """
    _name = "decrypt"

    def _execute(self, card) -> int:
        """
        Execute the decrypt command to decrypt data using ECIES

        :param card: The card instance
        :return: 0 if successful, other number indicating an issue
        :rtype: int
        """
        # Basic validation
        if cryptnox_sdk_py is None:
            print("Error: cryptnox_sdk_py library is not available")
            return -1

        if not hasattr(card, 'decrypt'):
            print("Error: Card does not support decrypt functionality")
            return -1

        print("=== Cryptnox CLI Decrypt Command ===")
        print(f"Card SN: {card.serial_number}")
        print(f"Initialized: {card.initialized}")
        print(f"Valid Key: {card.valid_key}")
        print(f"Seed Source: {card.seed_source}")

        try:
            # Get parameters from command line arguments
            mode = getattr(self.data, 'mode', 'symmetric')  # 'symmetric' or 'data'
            pubkey_hex = getattr(self.data, 'pubkey', '')
            encrypted_data_hex = getattr(self.data, 'data', '')
            pin = getattr(self.data, 'pin', '')

            # Authenticate with PIN first (following simple_pubkey_example pattern)
            if pin:
                print("\nAuthenticating with PIN...")
                try:
                    card.verify_pin(pin)
                    print("PIN authentication successful!")
                except Exception as e:
                    print(f"PIN authentication failed: {e}")
                    return -1
            else:
                print("Warning: No PIN provided. This will only work if user key authentication was performed.")

            # Handle public key - if not provided, generate ephemeral key pair (following simple_pubkey_example)
            if not pubkey_hex:
                print("\nNo public key provided. Generating ephemeral key pair...")
                try:
                    # Generate ephemeral key pair for ECDH using cryptography library (SECP256R1)
                    from cryptography.hazmat.primitives.asymmetric import ec
                    from cryptography.hazmat.primitives import serialization
                    from cryptography.hazmat.backends import default_backend

                    # Generate private key using SECP256R1 (P-256) curve
                    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
                    public_key = private_key.public_key()

                    # Get uncompressed public key (65 bytes, 0x04 prefix)
                    public_key_bytes = public_key.public_bytes(
                        encoding=serialization.Encoding.X962,
                        format=serialization.PublicFormat.UncompressedPoint
                    )
                    pubkey_hex = public_key_bytes.hex()

                    print("Generated ephemeral key pair")
                    print(f"Ephemeral public key: {pubkey_hex}")
                    print(f"Length: {len(public_key_bytes)} bytes")

                except Exception as e:
                    print(f"Failed to generate ephemeral key pair: {e}")
                    print("Use --pubkey to specify the public key in hex format")
                    return -1
            else:
                print(f"Using provided public key: {pubkey_hex[:32]}...")

            # Convert hex strings to bytes
            try:
                pubkey = bytes.fromhex(pubkey_hex)
            except ValueError:
                print("Error: Invalid public key format. Must be hex string.")
                return -1

            # Validate public key format
            if len(pubkey) != 65:
                print("Error: Public key must be 65 bytes (X9.62 uncompressed format)")
                print(f"Received: {len(pubkey)} bytes")
                print("Expected format: 0x04 followed by two 32-byte coordinates")
                return -1

            if pubkey[0] != 0x04:
                print("Error: Public key must be in X9.62 uncompressed format (0x04|X|Y)")
                print(f"Received prefix: 0x{pubkey[0]:02x}")
                print("Expected prefix: 0x04")
                return -1

            # Determine P1 parameter
            if mode == 'symmetric':
                print("Mode: Output symmetric key")
            elif mode == 'data':
                print("Mode: Decrypt data")

                if not encrypted_data_hex:
                    print("Error: Encrypted data is required for data decryption mode")
                    print("Use --data to specify the encrypted data in hex format")
                    return -1

                try:
                    encrypted_data = bytes.fromhex(encrypted_data_hex)
                except ValueError:
                    print("Error: Invalid encrypted data format. Must be hex string.")
                    return -1

                # Validate encrypted data length (must be multiple of 16 bytes for AES)
                if len(encrypted_data) % 16 != 0:
                    print("Error: Encrypted data length must be multiple of 16 bytes (AES block size)")
                    print(f"Current length: {len(encrypted_data)} bytes")
                    return -1
            else:
                print("Error: Invalid mode. Use 'symmetric' or 'data'")
                return -1

            print(f"Public key: {pubkey_hex[:32]}...")
            if mode == 'data':
                print(f"Encrypted data length: {len(encrypted_data)} bytes")

            # Validate PIN format if provided
            if pin:
                if len(pin) > 9:
                    print("Error: PIN too long (maximum 9 characters)")
                    return -1
                if not pin.isdigit():
                    print("Error: PIN must contain only digits")
                    return -1

            print("\n=== Executing Decrypt Command ===")

            try:
                # Execute the decrypt command (following simple_pubkey_example pattern)
                if mode == 'symmetric':
                    print("Getting symmetric key...")
                    result = card.decrypt(p1=0, pubkey=pubkey, pin=pin)
                    print("Symmetric key generated successfully")
                    print(f"Length: {len(result)} bytes")
                    print(f"Symmetric key: {result.hex()}")

                else:  # mode == 'data'
                    print("Decrypting data...")
                    result = card.decrypt(p1=1, pubkey=pubkey, encrypted_data=encrypted_data, pin=pin)
                    print("Data decrypted successfully")
                    print(f"Length: {len(result)} bytes")
                    print(f"Decrypted data: {result.hex()}")

                    # Try to decode as text if it looks like text
                    try:
                        decoded_text = result.decode('utf-8').rstrip('\x00')
                        print(f"Decrypted text: {decoded_text}")
                    except UnicodeDecodeError:
                        print("Decrypted data is binary (not text)")

                print("\nDecrypt command completed successfully!")
                return 0

            except cryptnox_sdk_py.exceptions.SeedException:
                print("Error: No seed/key loaded")
                print("Please load a seed first: cryptnox seed")
                return -1
            except cryptnox_sdk_py.exceptions.PinException:
                print("Error: PIN is not correct")
                print("Please provide the correct PIN")
                return -1
            except cryptnox_sdk_py.exceptions.DataValidationException as e:
                print(f"Error: Data validation failed - {e}")
                print("Please check your input parameters")
                return -1
            except cryptnox_sdk_py.exceptions.SecureChannelException:
                print("Error: Secure channel communication failed")
                print("Please ensure the card is properly connected and authenticated")
                return -1
            except Exception as e:
                print(f"Unexpected error: {e}")
                print("Please check your input parameters and try again")
                return -1

        except Exception as e:
            print(f"Unexpected error: {e}")
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
        Add command line options for the decrypt command

        :param subparsers: Argument parser subparsers
        """
        decrypt_parser = subparsers.add_parser(
            "decrypt",
            help="Decrypt data using ECIES (Elliptic Curve Integrated Encryption Scheme)"
        )

        decrypt_parser.add_argument(
            "--mode",
            choices=['symmetric', 'data'],
            default='symmetric',
            help="Decryption mode: 'symmetric' outputs symmetric key, 'data' decrypts data (default: symmetric)"
        )

        decrypt_parser.add_argument(
            "--pubkey",
            type=str,
            required=False,
            help="Public key in hex format (65 bytes, X9.62 uncompressed format). "
                 "If not provided, will be retrieved from card automatically."
        )

        decrypt_parser.add_argument(
            "--data",
            type=str,
            default='',
            help="Encrypted data in hex format (required for data mode, must be multiple of 16 bytes)"
        )

        decrypt_parser.add_argument(
            "--pin",
            type=str,
            default='',
            help="PIN code (optional if user key authentication was performed)"
        )
