# -*- coding: utf-8 -*-
"""
Module containing command for unlocking the pin
"""

from .command import Command
from .helper import security

try:
    import enums
except ImportError:
    from .. import enums


class UnlockPin(Command):
    """
    Command to unlock card PIN code.
    """
    _name = enums.Command.UNLOCK_PIN.value

    def _execute(self, card) -> int:
        card.check_init()

        security.process_command_with_puk(card, self.unblock_pin, card)

        print("PIN code successfully changed.")

        return 0

    @staticmethod
    def unblock_pin(card, puk):
        is_easy_mode = security.is_easy_mode(card.info)
        if is_easy_mode:
            pin_code = security.EASY_MODE_PIN
        else:
            pin_code = security.confirm_pin_code(card, f"Set card PIN code ({card.pin_rule}): ")

        card.unblock_pin(puk, pin_code)

        if is_easy_mode:
            print(f"Easy mode card setting easy mode PIN code: {security.EASY_MODE_PIN}")
