# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing Windows Hello user key handling.
"""

import sys

if sys.platform.startswith("win"):
    from .hello import Hello  # noqa: F401

    __all__ = ["Hello"]
