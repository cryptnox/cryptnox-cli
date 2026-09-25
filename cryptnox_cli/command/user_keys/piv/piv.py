# -*- coding: utf-8 -*-
"""
Module for working with PIV based on UserKey class.
"""
from hashlib import sha256

import cryptnox_sdk_py
from cryptography import x509
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding

from . import piv_card
from .. import user_key_base
from ...helper.masked_input import getpass


class Piv(user_key_base.UserKey):
    """
    Class for handling PIV operations compatible with UserKey class
    """
    name = "piv"
    description = "PIV applet"
    slot_index = cryptnox_sdk_py.SlotIndex.EC256R1
    custom_bit = 0

    def delete(self):
        pass

    @property
    def public_key(self) -> bytes:
        try:
            with piv_card.PIVcard() as current_card:
                cert_raw = current_card.get_data("5FC10A")
        except piv_card.PIVBaseException as error:
            raise user_key_base.ProcessingException(error) from error

        try:
            cert = x509.load_der_x509_certificate(cert_raw[4:-5])
        except ValueError as error:
            raise user_key_base.ProcessingException(error) from error

        return cert.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

    def sign(self, message: bytes) -> bytes:
        try:
            with piv_card.PIVcard() as current_card:
                Piv._verify_piv_pin(current_card)
                signature = current_card.sign(0x9C, 0x11, sha256(message).digest())
        except piv_card.NotFoundException as error:
            raise user_key_base.NotFoundException(error) from error
        except piv_card.PIVBaseException as error:
            raise user_key_base.ProcessingException(error) from error

        return signature

    @staticmethod
    def _verify_piv_pin(card: piv_card.PIVcard):
        if card.is_locked(0x80):
            print("\nThis PIV is locked. Use an external tool to unlock it.\n")
            raise user_key_base.ProcessingException

        while True:
            pin_code = getpass(prompt="PIV PIN code: ")
            if pin_code.lower() == "exit":
                raise user_key_base.ExitException("The request was canceled by the user")

            if not pin_code.isnumeric or not 6 <= len(pin_code) <= 8:
                print("PIN code must be all numbers and it's length needs to be between 6 and 8 "
                      "characters")
                continue

            try:
                return card.verify_pin(0x80, pin_code)
            except piv_card.PinException as error:
                if error.retries_left == 0:
                    raise
                try_str = "tries" if error.retries_left > 1 else "try"
                print(f"Wrong pin code. You have {error.retries_left} {try_str} before the card is locked.")
