# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for Ethereum-specific command-line argument parsing and validation,
including transaction parameters, gas settings, and network configuration.
"""

from decimal import Decimal, InvalidOperation

import argparse

from .common import (
    add_config_sub_parser,
    add_pin_option
)
from ..helper.helper_methods import try_eval

try:
    import enums
except ImportError:
    from ... import enums


def _validate_decimal(value: str) -> Decimal:

    try:
        return Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(
            f"Invalid amount: '{value}'. Please provide a valid number"
        )


def _argument_parser(arguments):
    return arguments if arguments.startswith("0x") else try_eval(arguments)


def _network_choices():
    return [e.name.lower() for e in enums.EthNetwork]


def _validate(address: str) -> str:
    try:
        int(address, 16)
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid ETH address")

    if not (address.startswith("0x") and len(address) in (40, 42)):
        raise argparse.ArgumentTypeError("Not a valid ETH address")

    return address


def _add_options(sub_parser):
    sub_parser.add_argument("-n", "--network",
                            choices=_network_choices(),
                            help="Network to use for transaction")
    sub_parser.add_argument("-p", "--price", type=int, help="Gas price")
    sub_parser.add_argument("-l", "--limit", type=int, help="Gas limit")


def _add_contract_options(subparsers):
    def _add_add(subparsers):
        sub_parser = subparsers.add_parser("add",
                                           help="Add contract to application "
                                                "to be later called with an "
                                                "alias")
        sub_parser.add_argument("alias", help="Alias for the application to recognize the "
                                              "contract by")
        sub_parser.add_argument("address", type=_validate, help="Address of the contract")
        sub_parser.add_argument("abi", type=str, nargs="+", help="ABI of the contract in a "
                                                                 "JSON format or ERC code")
        sub_parser.add_argument("-n", "--network", choices=_network_choices(),
                                help="Network to use for transaction")

    def _add_call(subparsers):
        sub_parser = subparsers.add_parser("call", help="Call a contract function")

        sub_parser.add_argument("alias", help="Alias for the application to recognize the "
                                              "contract by")
        sub_parser.add_argument("function", help="Name of the function to call")
        sub_parser.add_argument("arguments", nargs="*", default=[], type=_argument_parser,
                                help="Arguments for the function")

    def _add_list(subparsers):
        sub_parser = subparsers.add_parser("list", help="List all contract aliases and their "
                                                        "connected addresses or contract "
                                                        "functions")

        sub_parser.add_argument("alias", nargs="?",
                                help="Alias of the contract which functions to list. If given "
                                     "list all function the contract has.")
        sub_parser.add_argument("-e", "--event", action="store_true",
                                help="List events of the selected contract")

    def _add_logs(subparsers):
        sub_parser = subparsers.add_parser("list_events", help="List events that have been "
                                                               "triggered since last running "
                                                               "of this command")
        sub_parser.add_argument("alias", help="Name of the contract to list events for")
        sub_parser.add_argument("event", help="Name of the event to list")

    def _add_transact(subparsers):
        sub_parser = subparsers.add_parser("transact", help="Call a contract function")

        sub_parser.add_argument("alias", help="Alias for the application to recognize the "
                                              "contract by")
        sub_parser.add_argument("function", help="Name of the function to call")
        sub_parser.add_argument("arguments", nargs="*", default=[], type=_argument_parser,
                                help="Arguments for the function")
        _add_options(sub_parser)

    sub_parser = subparsers.add_parser("contract", help="Smart contract operations")

    action_sub_parser = sub_parser.add_subparsers(dest="contract_action", required=True,
                                                  help="Action to execute")
    _add_add(action_sub_parser)
    _add_call(action_sub_parser)
    _add_list(action_sub_parser)
    _add_transact(action_sub_parser)
    _add_logs(action_sub_parser)


def _add_send(subparsers):
    sub_parser = subparsers.add_parser("send", help="Simple command to send Ethereum system token")
    sub_parser.add_argument("address", type=_validate, help="Address where to send funds")
    sub_parser.add_argument("amount", type=_validate_decimal, help="Amount to send")
    sub_parser.add_argument("-c", "--contract", type=_validate,
                            help="Contract address of the contract")

    _add_options(sub_parser)


def options(subparsers, pin_option: bool):
    eth_sub_parser = subparsers.add_parser(enums.Command.ETH.value, help="Ethereum subcommands")

    if pin_option:
        add_pin_option(eth_sub_parser)

    action_sub_parser = eth_sub_parser.add_subparsers(dest="eth_action", required=True)

    _add_send(action_sub_parser)
    _add_contract_options(action_sub_parser)
    add_config_sub_parser(action_sub_parser, "Ethereum")
