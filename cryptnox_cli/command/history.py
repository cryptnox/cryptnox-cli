# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for getting history of the card
"""
from tabulate import tabulate

from .command import Command

try:
    import enums
except ImportError:
    from .. import enums


def history_generator(card, start=0, stop=20):
    index = start

    while index < start + stop:
        data = card.history(index)
        if data.signing_counter == 0:
            break
        yield data
        index += 1


class History(Command, ):
    _ENTRIES_PER_PAGE = 25

    _name = enums.Command.HISTORY.value

    def _execute(self, card) -> int:
        self._check(card)

        page = self.data.page
        number_of_entries = card.signing_counter
        number_of_pages = number_of_entries // History._ENTRIES_PER_PAGE + 1

        print(f"There are {number_of_entries} entries in the signing history\n")

        if page > number_of_pages:
            print("Not enough entries in history to show.")
            return 0

        history = []

        headers = ["Signing counter", "Hashed message"]

        start = (page - 1) * History._ENTRIES_PER_PAGE
        for data in history_generator(card, start, History._ENTRIES_PER_PAGE):
            history.append([data.signing_counter, data.hashed_data.hex()])

        print(tabulate(history, headers=headers))

        print(f"Listing page {page} of {number_of_pages}")

        return 0
