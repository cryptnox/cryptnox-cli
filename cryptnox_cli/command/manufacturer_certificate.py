# -*- coding: utf-8 -*-
"""
Module containing command for retrieving and displaying manufacturer certificate
"""
import re
import cryptnox_sdk_py
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .command import Command

try:
    import enums
except ImportError:
    from .. import enums


class ManufacturerCertificate(Command):
    """
    Command to retrieve and display the manufacturer certificate from the card
    """
    _name = enums.Command.CERTIFICATE.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        print("Retrieving manufacturer certificate from the card...")
        try:
            # Check if the card object has the required method
            if not hasattr(card, 'get_manufacturer_certificate'):
                print("Error: The current card type does not support retrieving a manufacturer certificate.")
                return -1

            cert_raw = card.get_manufacturer_certificate(hexed=False)
            if not cert_raw:
                print("Error: Could not retrieve manufacturer certificate from the card.")
                return -1

            # Parse the certificate
            cert = x509.load_der_x509_certificate(cert_raw)

            # Format and display the certificate
            self._print_certificate_text(cert)

            return 0
        except Exception as e:
            print(f"Error retrieving or processing manufacturer certificate: {e}")
            return -1

    def _print_certificate_text(self, cert: x509.Certificate):
        """
        Prints the certificate in a human-readable format similar to openssl x509 -text
        """
        print("Certificate Data:")
        print(f"    Version: {cert.version.value + 1} (0x{cert.version.value})")
        print("    Serial Number:")
        serial_hex = self._format_hex(cert.serial_number)
        print(f"        {serial_hex}")
        sig_alg_name = cert.signature_algorithm_oid._name
        sig_alg = re.sub(r'(with-)([a-z0-9]+)', lambda m: m.group(1) + m.group(2).upper(), sig_alg_name)
        print(f"    Signature Algorithm: {sig_alg}")
        print(f"    Issuer: {self._format_name(cert.issuer)}")
        print("    Validity:")
        # Use UTC for consistency as required by the GMT format in example
        print(f"        Not Before: {cert.not_valid_before_utc.strftime('%b %d %H:%M:%S %Y GMT')}")
        print(f"        Not After : {cert.not_valid_after_utc.strftime('%b %d %H:%M:%S %Y GMT')}")
        print(f"    Subject: {self._format_name(cert.subject)}")

        public_key = cert.public_key()
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            print("    Subject Public Key Info:")
            print("        Public Key Algorithm: id-ecPublicKey")
            print(f"            Public-Key: ({public_key.key_size} bit)")
            print("            pub:")
            pub_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            pub_hex = ':'.join(f'{b:02x}' for b in pub_bytes)
            self._print_indented_hex(pub_hex, 16)
            print(f"            ASN1 OID: {public_key.curve.name}")
            if public_key.curve.name in ["prime256v1", "secp256r1"]:
                print("            NIST CURVE: P-256")

        print(f"Signature Algorithm: {sig_alg}")
        print("Signature Value:")
        sig_hex = ':'.join(f'{b:02x}' for b in cert.signature)
        self._print_indented_hex(sig_hex, 4)

    def _format_hex(self, value: int) -> str:
        h = hex(value)[2:]
        if len(h) % 2 != 0:
            h = '0' + h
        return ':'.join(h[i:i+2] for i in range(0, len(h), 2))

    def _print_indented_hex(self, hex_str: str, indent: int):
        parts = hex_str.split(':')
        line_size = 15
        for i in range(0, len(parts), line_size):
            chunk = parts[i:i+line_size]
            line = ":".join(chunk)
            if i + line_size < len(parts):
                line += ":"
            print(" " * indent + line)

    def _format_name(self, name: x509.Name) -> str:
        short_names = {
            "commonName": "CN",
            "organizationName": "O",
            "countryName": "C",
            "localityName": "L",
            "stateOrProvinceName": "ST",
            "organizationalUnitName": "OU"
        }
        parts = []
        # Reverse to match common OpenSSL display order (Subject/Issuer)
        for attribute in reversed(list(name)):
            name_str = attribute.oid._name
            short_name = short_names.get(name_str, name_str)
            parts.append(f"{short_name}={attribute.value}")
        return ", ".join(parts)
