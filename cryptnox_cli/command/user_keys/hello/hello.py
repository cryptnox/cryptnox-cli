# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for handling user authentication using Windows Hello.

Warning: Windows hello functions are called in separate thread as calling
the script as module will set the thread mode and windows also sets it on import

RuntimeError: Cannot change thread mode after it is set.
"""

import concurrent.futures
import sys

import cryptnox_sdk_py
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from . import exceptions
from .. import user_key_base


class Hello(user_key_base.UserKey):
    """
    Class for handling Windows Hello operations compatible with UserKey class
    """
    name = "hello"
    description = "Windows Hello"
    priority = 100
    slot_index = cryptnox_sdk_py.SlotIndex.RSA
    custom_bit = 2

    def __init__(self, target: str = ""):
        if not sys.platform.startswith("win"):
            raise user_key_base.NotSupportedException("Only supported on windows platform")

        super().__init__(target)

    def delete(self):
        def _thread_delete_key(name):
            from .windows_hello import delete
            delete(name)

        self._execute(_thread_delete_key)

    @property
    def public_key(self) -> bytes:
        def _thread_get_public_key(name):
            from .windows_hello import get_public_key
            return get_public_key(name)

        public_key = serialization.load_der_public_key(self._execute(_thread_get_public_key),
                                                       backend=default_backend())

        return public_key.public_numbers().n.to_bytes(256, byteorder='big')

    def sign(self, message: bytes) -> bytes:
        def _thread_sign(name, message_to_sign):
            from .windows_hello import sign
            return sign(name, message_to_sign)

        return self._execute(_thread_sign, message.hex())

    def _execute(self, method, *args):
        if not sys.platform.startswith("win"):
            raise user_key_base.NotSupportedException("Hello is only supported on windows")

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(method, self._target, *args)
                result = future.result()
        except exceptions.NotFoundException as error:
            raise user_key_base.NotFoundException(error) from error
        except exceptions.CanceledException as error:
            raise user_key_base.ExitException(error) from error
        except (ModuleNotFoundError, exceptions.NotSupportedException) as error:
            raise user_key_base.NotSupportedException(error) from error
        except exceptions.WindowsHelloExceptions as error:
            raise user_key_base.ProcessingException(error) from error

        return result
