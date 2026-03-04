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


class ChangePuk(Command):
    """
    Command to change the PIN code of the card
    """
    _name = enums.Command.CHANGE_PUK.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        if not card.initialized:
            ui.print_warning("Card is not initialized")
            print("To initialize card run : init\nTo initialize card in easy mode run : init -e")

            return -1

        easy_mode = security.is_easy_mode(card.info)

        while True:
            if easy_mode:
                puk_code = security.easy_mode_puk(card)
                print(f"Card is in {security.EASY_MODE_TEXT}. Setting same PUK code automatically.")
                new_puk_code = puk_code
            else:
                puk_code = security.get_puk_code(card)
                new_puk_code = security.get_puk_code(card, f"Set new PUK code ({card.puk_rule}): ")

            try:
                card.change_puk(puk_code, new_puk_code)
                break
            except cryptnox_sdk_py.exceptions.PukException:
                if easy_mode:
                    print(f"{security.EASY_MODE_TEXT} PUK doesn't work. Try other PUK code.\n")
                    easy_mode = False
                else:
                    print("Wrong PUK code. Try again.")

        if not easy_mode:
            print("PUK changed successfully")

        return 0
