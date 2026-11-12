# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for handling configuration file
"""

from .command import Command
from .helper.config import (
    write_config,
    print_config,
    print_key_config,
    print_section_config
)

try:
    import enums
except ImportError:
    from .. import enums


class Config(Command):
    """
    Command for handling configuration file
    """
    _name = enums.Command.CONFIG.value

    def _execute(self, card) -> int:
        self._check(card)

        if self.data.value:
            return write_config(card, self.data.section, self.data.key, self.data.value)
        if self.data.key:
            return print_key_config(card, self.data.section, self.data.key)
        if self.data.section:
            return print_section_config(card, self.data.section)

        print_config(card)

        return 0
