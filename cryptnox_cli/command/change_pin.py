# -*- coding: utf-8 -*-
"""
Module containing command for changing PIN code of the card
"""
import cryptnox_sdk_py

from .command import Command
from .helper import (
    security,
    ui
)

try:
    import enums
except ImportError:
    from .. import enums


class ChangePin(Command):
    """
    Command to change the PIN code of the card
    """
    _name = enums.Command.CHANGE_PIN.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        if not card.initialized:
            ui.print_warning("Card is not initialized")
            print("To initialize card run : init\nTo initialize card in easy mode run : init -e")

            return -1

        if card.auth_type != cryptnox_sdk_py.AuthType.PIN:
            security.check_pin_code(card)

        if security.is_easy_mode(card.info):
            print("Card is in easy mode. Setting same PIN code")
            pin_code = security.EASY_MODE_PIN
        else:
            pin_code = security.confirm_pin_code(card, f"Set new PIN code ({card.pin_rule}): ")

        card.change_pin(pin_code)

        print("PIN changed successfully")

        return 0
