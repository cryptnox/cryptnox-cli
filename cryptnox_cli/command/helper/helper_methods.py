"""
Module providing various utility functions including dictionary operations,
input validation, cryptographic operations, and other common helper methods
used throughout the application.
"""

import ast
from collections.abc import Mapping
from typing import Any

import argparse
import cryptnox_sdk_py

from . import security
from .. import user_keys


def deep_update(source, overrides):
    """
    Update a nested dictionary or similar mapping.
    Modify ``source`` in place.
    """
    for key, value in overrides.items():
        if isinstance(value, Mapping) and value:
            returned = deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source


class IntRange:
    def __init__(self, imin: int = None, imax: int = None):
        self._imin = imin
        self._imax = imax

    def __call__(self, arg: Any):
        try:
            value = int(arg)
        except ValueError:
            raise self.exception()

        if (self._imin is not None and value < self._imin) or \
                (self._imax is not None and value > self._imax):
            raise self.exception()

        return value

    def exception(self):
        if self._imin is not None and self._imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer in the range [{self._imin}, "
                                              f"{self._imax}]")
        elif self._imin is not None:
            return argparse.ArgumentTypeError(f"Must be an integer >= {self._imin}")
        elif self._imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer <= {self._imax}")
        else:
            return argparse.ArgumentTypeError("Must be an integer")


def sign(card: cryptnox_sdk_py.Card, message: bytes,
         derivation: cryptnox_sdk_py.Derivation = cryptnox_sdk_py.Derivation.CURRENT_KEY,
         key_type: cryptnox_sdk_py.KeyType = cryptnox_sdk_py.KeyType.K1, path: str = "",
         pin_code: str = "") -> bytes:
    """
    Open the card with a user key or PIN code and sign the given message in the given card

    :param crypnoxpy.Card card: Card to use for signature
    :param bytes message: Message to sign with the card
    :param cryptnox_sdk_py.Derivation derivation: Derivation to use when signing
    :param cryptnox_sdk_py.KeyType key_type: Key type to use when signing
    :param str path: Path to use for signature generation
    :param str pin_code: If PIN code is given use it instead of asking for it

    :return: Signature of the message generated in the card
    :rtype: bytes
    """
    signature = None

    if user_keys.authenticate(card, message):
        signature = card.sign(message, derivation, key_type, path)

    if not signature:
        if not pin_code:
            pin_code = security.check_pin_code(card)
        signature = card.sign(message, derivation, key_type, path, pin_code)

    if not signature:
        raise ValueError("Error in getting the signature")

    return signature


def try_eval(value: str) -> Any:
    """
    Returns appropriate type for a string

    :param value: Value to evaluate
    :return: Evaluated value
    """
    try:
        value = ast.literal_eval(value)
    except ValueError:
        # Not a literal; keep the original string value
        pass
    return value
