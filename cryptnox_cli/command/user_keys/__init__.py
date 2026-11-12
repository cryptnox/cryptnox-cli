# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for authenticating the card with third party providers
"""
from .authentication import (  # noqa: F401
    add,
    authenticate,
    delete,
    get
)

__all__ = ["add", "authenticate", "delete", "get"]
