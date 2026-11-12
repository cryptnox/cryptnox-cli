# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for common argument parsing utilities and validation functions
used across different command-line options and subcommands.
"""

import argparse
import re


def add_pin_option(sub_parser):
    sub_parser.add_argument("-p", "--pin", nargs=1, type=pin_validator,
                            help="Use pin for the command")


def add_config_sub_parser(sub_parser, crypto_currency: str) -> None:
    """
    Add config subparser

    :param sub_parser: Parser object to be added to
    :param crypto_currency: Name of the cryptocurrency
    :return: None
    """
    parser = sub_parser.add_parser("config",
                                   help=f"View or edit {crypto_currency} "
                                   "configuration")
    parser.add_argument("key", nargs="?", type=str, default=None,
                        help="Define key to use")
    parser.add_argument("value", nargs="?", type=str, default=None,
                        help="Define a new value for the given section "
                             "and key")


def pin_validator(value: str):
    """
    Checks if pin is in correct format.

    :param str value: Pin to check if valid
    :return: Given value
    :raises argparse.ArgumentTypeError: When value is not valid
    """
    pattern = re.compile(r"^\d{4,9}$")

    if not pattern.match(value):
        raise argparse.ArgumentTypeError("ERROR when input the PIN code, "
                                         "must be between 4 and 9 digits.")

    return value
