# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for resetting content of card to factory default
"""
import cryptnox_sdk_py

from .helper import security
from .command import Command

try:
    import enums
except ImportError:
    from .. import enums


class Reset(Command):
    """
    Command to reset the card to its factory settings.

    Warning: This command will delete the keys from the card, which may result
             in loss of access to the funds.
    """
    _name = enums.Command.RESET.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        if not card.initialized:
            print("Card is not initialized. Already cleared.")
            return 0

        serial_number = card.serial_number
        security.process_command_with_puk(card, card.reset)

        del self._cards[serial_number]
        print("Card was reset successfully.")

        return 0
