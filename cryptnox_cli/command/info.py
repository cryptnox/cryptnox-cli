# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for showing information about accounts on the card to the user
"""
from .command import Command

from . import erc_token
from . import card as card_command

try:
    import enums
except ImportError:
    from .. import enums


class Info(Command):
    """
    Command to get detailed information about the accounts on the card
    """
    _name = enums.Command.INFO.value

    def _execute(self, card) -> int:
        card_types = {
            ord("N"): erc_token.Info,
            ord("B"): card_command.Info,
        }

        try:
            command = card_types[card.type](self.data, self._cards)
        except KeyError:
            print("Method not supported with this card type.")
            return -2

        return command.execute(card)
