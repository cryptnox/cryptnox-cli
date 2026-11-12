# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for working with user keys like:
YubiKey or Windows Hello
"""
import shutil

import cryptnox_sdk_py
from tabulate import tabulate

from . import user_keys
from .command import Command
from .helper import (
    security,
    ui
)

try:
    import enums
except ImportError:
    from .. import enums


class UserKey(Command):
    """
    Command to work with user keys.
    """
    _name = enums.Command.USER_KEY.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        if card.type != ord("B"):
            print("Method not supported with this card type.")
            return -2

        if self.data.subaction == "list":
            return self._list(card)

        if not card.initialized:
            ui.print_warning("Card is not initialized")
            print(f"To initialize card run : init\n"
                  f"To initialize card in {security.EASY_MODE_TEXT} run : init -e")

            return -1

        if self.data.subaction == "add":
            return UserKey._add(card, self.data.type, " ".join(self.data.description))
        if self.data.subaction == "delete":
            return UserKey._delete(card, self.data.type)

        return -1

    @staticmethod
    def _add(card: cryptnox_sdk_py.Card, auth_type: str, description: str = "") -> int:
        result = -1
        if card.user_key_enabled(user_keys.get()[auth_type]):
            print("Card has already key of this type.")
            return -1

        if security.process_command_with_puk(card, user_keys.add, auth_type, card, description):
            print("User key added")
            result = 0

        return result

    @staticmethod
    def _delete(card: cryptnox_sdk_py.Card, auth_type: str) -> int:
        result = -1
        if not card.user_key_enabled(user_keys.get()[auth_type]):
            print("Target key not found.")
            return -1

        if security.process_command_with_puk(card, user_keys.delete, auth_type, card):
            print("User key deleted.")
            result = 0

        return result

    def _list(self, card: cryptnox_sdk_py.Card) -> int:
        slots = user_keys.get(card)
        data = [[name] for name, slot in slots.items() if card.user_key_enabled(slot)]

        if not data:
            print("No user keys registered in card")
            return 0

        self._check(card)

        large_screen = shutil.get_terminal_size((80, 20)).columns > 200
        key_length = 130 if large_screen else 32
        headers = ["Type", "Description", "Public Key"]

        for row in data:
            slot = slots[row[0]]
            description, public_key = card.user_key_info(slot)
            row.append(description)
            row.append("\n".join([public_key[i:i + key_length] for i in range(0, len(public_key), key_length)]))

        print(tabulate(data, headers=headers))

        return 0
