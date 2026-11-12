# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing command for Unknown
"""
from argparse import Namespace

from .command import Command


class Unknown(Command):
    """
    Class that should be returned when none of the other are sufficient to
    process the user request

    The command doesn't do anything.
    """
    _name = "unknown"

    def execute(self, serial_number: int = None) -> int:
        """
        Main execution method of the command.

        Finds card and establishes connection to it. Executes _execute method.

        :param serial_number: Serial number of the wanted card
        :return: 0 if the command executed without issues. Other number
                 indicating and issue
        :rtype: int
        """
        print("Command not recognized")

        return -1

    def _execute(self, card):
        pass

    @classmethod
    def meets_condition(cls, data: Namespace) -> bool:
        return False

    @staticmethod
    def add_options(subparsers) -> None:
        pass
