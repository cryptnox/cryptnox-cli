# -*- coding: utf-8 -*-
"""
Module for Solana-specific command-line argument parsing and validation,
including the send action, recipient address validation and network selection.
"""

from decimal import Decimal, InvalidOperation

import argparse
import base58

from .common import (
    add_config_sub_parser,
    add_pin_option
)

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


def _network_choices():
    return [e.name.lower() for e in enums.SolanaNetwork]


def _validate(address: str) -> str:
    try:
        decoded = base58.b58decode(address)
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid Solana address")

    if len(decoded) != 32:
        raise argparse.ArgumentTypeError("Not a valid Solana address")

    return address


def _add_send(subparsers):
    sub_parser = subparsers.add_parser("send", help="Simple command to send native SOL")
    sub_parser.add_argument("address", type=_validate, help="Address where to send funds")
    sub_parser.add_argument("amount", type=_validate_decimal, help="Amount to send")
    sub_parser.add_argument("-n", "--network", choices=_network_choices(),
                            help="Network to use for transaction")


def options(subparsers, pin_option: bool):
    solana_sub_parser = subparsers.add_parser(enums.Command.SOLANA.value,
                                              help="Solana subcommands")

    if pin_option:
        add_pin_option(solana_sub_parser)

    action_sub_parser = solana_sub_parser.add_subparsers(dest="solana_action", required=True)

    _add_send(action_sub_parser)
    add_config_sub_parser(action_sub_parser, "Solana")
