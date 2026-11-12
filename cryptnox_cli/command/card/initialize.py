# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for handling the initialization process of cards, including
setting up user credentials, PIN/PUK codes, and preparing the card for use
with cryptocurrency operations.
"""
from argparse import Namespace
from tabulate import tabulate

from ..cards import Cards
from ..helper import ui, security
from ..helper.cards import CardManager

__all__ = ['Cards']


class Initialize:
    def __init__(self, data: Namespace, cards: CardManager = None):
        self.data = data
        self._cards = cards or CardManager(self.data.verbose if "verbose" in self.data else False)
        self.serial_number = None

    def execute(self, card) -> int:
        if card.initialized:
            print("Card already initialized.")
            return 1

        print("Cryptnox Initialisation\n")

        init_data = ui.get_init_data(card, self.data.easy_mode)

        print("\nInitializing the applet\n")

        card.init(init_data.name, init_data.email, init_data.pin, init_data.puk)

        print("Card has been initialized.")
        if self.data.easy_mode:
            print(f"Card is in {security.EASY_MODE_TEXT}.\n\nPress enter for all pin and puk prompts.\n")

        print(tabulate([["RUN seed COMMAND TO GENERATE NEW OR LOAD AN EXISTING SEED."]],
                       tablefmt="rst"))

        del self._cards[card.serial_number]

        return 0
