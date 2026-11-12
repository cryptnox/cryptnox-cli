# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for showing list of available cards
"""

from .command import Command

try:
    import enums
except ImportError:
    from .. import enums


class Cards(Command):
    """
    Command to show a table of cards to the user
    """
    _name = enums.Command.CARD.value

    def execute(self, serial_number: int = None) -> int:
        """
        Base class method overridden to no initialize a card.

        :param serial_number: Serial number of the wanted card
        :return: 0 if the command executed without issues. Other number
                 indicating and issue
        :rtype: int
        """
        self._cards.refresh()
        self._cards.print_card_list(show_warnings=True, print_with_one_card=True)

        return 0

    def _execute(self, _) -> int:
        return 0
