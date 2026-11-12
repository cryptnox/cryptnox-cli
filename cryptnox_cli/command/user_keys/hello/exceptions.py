# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Exceptions Windows Hello can raise.
"""


class WindowsHelloExceptions(Exception):
    """Base exception for the class exceptions."""


class NotSupportedException(WindowsHelloExceptions):
    """There is no hardware support for Windows Hello."""


class UnknownErrorException(WindowsHelloExceptions):
    """An unknown error occurred."""


class NotFoundException(WindowsHelloExceptions):
    """The credential could not be found."""


class CanceledException(WindowsHelloExceptions):
    """The request was cancelled by the user."""


class UserPrefersPasswordException(WindowsHelloExceptions):
    """The user prefers to enter a password."""


class SecurityDeviceLockedException(WindowsHelloExceptions):
    """The security device was locked."""
