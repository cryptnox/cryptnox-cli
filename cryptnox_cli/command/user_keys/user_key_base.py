# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing base class for user key.
"""
import abc

import cryptnox_sdk_py


class UserKeyException(Exception):
    """
    Base exception for all exceptions for UserKey
    """


class ExitException(UserKeyException):
    """
    The user has exited the request
    """


class NotFoundException(UserKeyException):
    """
    The user key hasn't been found
    """


class NotSupportedException(UserKeyException):
    """
    The user key is not supported
    """


class ProcessingException(UserKeyException):
    """
    There was an issue in processing the user key
    """


class UserKey(metaclass=abc.ABCMeta):
    """
    Base class on top of which other user key classes should be implemented
    """
    priority: int = 0

    def __init__(self, target: str = ""):
        self._target: str = target

    @abc.abstractmethod
    def delete(self) -> None:
        """
        Delete the key from the user key provider
        """

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        :return: Description of the user key service
        :rtype: str
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        :return: Name of the user key service
        :rtype: str
        """

    @property
    @abc.abstractmethod
    def public_key(self) -> bytes:
        """
        :return: Public key of the user key service
        :rtype: bytes
        """

    @abc.abstractmethod
    def sign(self, message: bytes) -> bytes:
        """
        Get signature of message from user key service

        :param bytes message: Message to sign

        :return: Signature of the given message
        :rtype: bytes
        """

    @property
    @abc.abstractmethod
    def slot_index(self) -> cryptnox_sdk_py.SlotIndex:
        """
        :return: Compatible slot index on the card
        :rtype: cryptnox_sdk_py.SlotIndex
        """

    @property
    def custom_bit(self) -> int:
        """
        :return: Custom bit to use for checking if method is enabled, -1 for not used
        :rtype: int
        """

        return -1

    def added(self, card):
        if self.custom_bit == -1:
            return

        card.custom_bits[self.custom_bit] = 1

    @classmethod
    def __subclasshook__(cls, c):
        if cls is UserKey:
            attrs = set(dir(c))

            if set(cls.__abstractmethods__) <= attrs:
                return True

        return NotImplemented

    @classmethod
    def enabled(cls, card: cryptnox_sdk_py.Card) -> bool:
        return card.user_key_enabled(cls.slot_index) and cls._custom_bit_enabled(card)

    @classmethod
    def _custom_bit_enabled(cls, card: cryptnox_sdk_py.Card) -> bool:
        try:
            return cls.custom_bit == -1 or card.custom_bits[cls.custom_bit]
        except IndexError:
            return True
