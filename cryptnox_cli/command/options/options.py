# -*- coding: utf-8 -*-
"""
Module for defining command-line argument parsers and subcommands
for various Cryptnox CLI operations including Bitcoin, Ethereum,
and card management commands.
"""

import re
from decimal import Decimal, InvalidOperation

import argparse

from . import eth
from .common import (
    add_config_sub_parser,
    add_pin_option
)
from .. import user_keys
from ..helper.helper_methods import IntRange

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


def add(parser, interactive: bool = False):
    subparsers = parser.add_subparsers(dest="command", help="Command options")

    _btc_options(subparsers, interactive)
    eth.options(subparsers, interactive)
    _transfer(subparsers, interactive)
    _info_options(subparsers, interactive)
    _history_options(subparsers, interactive)
    _config_options(subparsers, interactive)

    _card_configuration(subparsers, interactive)
    _change_pin_options(subparsers, interactive)
    _change_puk_options(subparsers, interactive)
    _user_key_options(subparsers, interactive)
    _unlock_pin_options(subparsers, interactive)

    _list_options(subparsers, interactive)

    _initialize_options(subparsers, interactive)
    _seed_options(subparsers, interactive)
    _reset_options(subparsers, interactive)

    _server_options(subparsers, interactive)
    _xpub_options(subparsers, interactive)
    _get_clearpubkey_options(subparsers, interactive)
    _decrypt_options(subparsers, interactive)
    _cert_options(subparsers, interactive)

    if interactive:
        use_sub_parser = subparsers.add_parser("use", help="Change card to be used by default")
        use_sub_parser.add_argument("serial_index", type=int, nargs="?",
                                    help="Serial number or index of card to be used")
        subparsers.add_parser("exit", help="Full application exit")

    return subparsers


def _btc_options(subparsers, interactive_mode):
    def add_send(sub_parser):
        def _validate(address: str) -> str:
            if re.match('^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', address) or \
                    re.match('^[2nm][a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
                return address
            raise argparse.ArgumentTypeError("Not a valid BTC address")

        send_sub_parser = sub_parser.add_parser("send", help="Simple command to send Bitcoin "
                                                             "system token")
        send_sub_parser.add_argument("address", type=_validate,
                                     help="Address where to send funds")
        send_sub_parser.add_argument("amount", type=_validate_decimal, help="Amount to send")
        send_sub_parser.add_argument("-n", "--network", choices=["mainnet", "testnet"],
                                     help="Network to use for transaction")
        send_sub_parser.add_argument("-f", "--fees", type=int,
                                     help="Fees to pay for the transaction")

    btc_sub_parser = subparsers.add_parser(enums.Command.BTC.value, help="Bitcoin commands")
    if interactive_mode:
        add_pin_option(btc_sub_parser)

    action_sub_parser = btc_sub_parser.add_subparsers(dest="action", required=True)

    add_send(action_sub_parser)
    add_config_sub_parser(action_sub_parser, "Bitcoin")


def _card_configuration(subparsers, interactive_mode):
    sub_parser = subparsers.add_parser(enums.Command.CARD_CONFIGURATION.value,
                                       help="Show card configuration and set PIN-less path, "
                                            "PIN authentication ")

    if interactive_mode:
        add_pin_option(sub_parser)

    sub_parser.add_argument("key", nargs="?", type=str, default=None, choices=["pinless", "pin"],
                            help="Configuration to set")
    sub_parser.add_argument("value", nargs="?", type=str, default=None, choices=["yes", "no"],
                            help="Set/unset card configuration")


def _change_pin_options(subparsers, interactive_mode):
    sub_parser = subparsers.add_parser(enums.Command.CHANGE_PIN.value,
                                       help="Change PIN code of the card")

    if interactive_mode:
        add_pin_option(sub_parser)


def _change_puk_options(subparsers, _: bool):
    subparsers.add_parser(enums.Command.CHANGE_PUK.value, help="Change PUK code of the card")


def _config_options(subparsers, _: bool):
    sub_parser = subparsers.add_parser(enums.Command.CONFIG.value,
                                       help="Lists blockchain configurations per type")
    sub_parser.add_argument("section", nargs="?", type=str, default=None,
                            help="Define section to use")
    sub_parser.add_argument("key", nargs="?", type=str, default=None, help="Define key to use")
    sub_parser.add_argument("value", nargs="?", type=str, default=None,
                            help="Define a new value for the given section and key")


def _history_options(subparsers, interactive_mode):
    entries_per_page = 25
    number_of_history_entries = 148

    sub_parser = subparsers.add_parser(enums.Command.HISTORY.value,
                                       help="Lists performed signatures")

    number_of_pages = number_of_history_entries // entries_per_page + 1
    sub_parser.add_argument("page", nargs="?", type=IntRange(1, number_of_pages),
                            default=1, help="Page number to show")

    if interactive_mode:
        add_pin_option(sub_parser)


def _info_options(subparsers, pin_options: bool):
    sub_parser = subparsers.add_parser(enums.Command.INFO.value,
                                       help="Default accounts information")

    if pin_options:
        add_pin_option(sub_parser)


def _initialize_options(subparsers, _: bool):
    sub_parser = subparsers.add_parser(enums.Command.INITIALIZE.value, help="Initialize a card")

    sub_parser.add_argument("-e", "--easy_mode", action="store_true", default=False,
                            help="Initialize card in easy mode. Set PIN and PUK code to all 0")


def _list_options(subparsers, _: bool):
    subparsers.add_parser(enums.Command.CARD.value, help="List all cards")


def _server_options(subparsers, _: bool):
    sub_parser = subparsers.add_parser(enums.Command.SERVER.value,
                                       help="Create a server or establish connection to server")
    sub_parser.add_argument('--port', nargs='?', type=int, default=5050,
                            help='Define port to server port, default 5050')
    sub_parser.add_argument('--host', nargs='?', type=str, default='0.0.0.0',
                            help='Define port to server host, default 0.0.0.0')


def _reset_options(subparsers, _: bool):
    subparsers.add_parser(enums.Command.RESET.value, help="Reset card")


def _seed_options(subparsers, interactive_mode):
    sub_parser = subparsers.add_parser(enums.Command.SEED.value, help="Generate seed for the card")

    if interactive_mode:
        add_pin_option(sub_parser)

    action_sub_parser = sub_parser.add_subparsers(dest="action", required=True)

    action_sub_parser.add_parser("chip", help="Generate new root key in the chip.")
    action_sub_parser.add_parser("dual", help="Generate same seed on two cards. "
                                              "(Requires two cards)")
    action_sub_parser.add_parser("recover", help="Recover a key from a BIP39 word list.")
    action_sub_parser.add_parser("upload", help="Generate seed in host, upload to card and show "
                                                "BIP39 word list for backup.")


def _unlock_pin_options(subparsers, _: bool):
    subparsers.add_parser(enums.Command.UNLOCK_PIN.value,
                          help="Set new PIN code for the card, PUK code required")


def _user_key_options(subparsers, _: bool):
    def _add_key_type_options(sub_parser):
        types = []

        names = user_keys.get().keys()
        for name in names:
            types.append(name)

        if types:
            sub_parser.add_argument("type", choices=types, help="Network to use for transaction")

    def _add_add_sub_parser(sub_parser):
        def description_type(value):
            if value.isalnum() and len(value) <= 64:
                return value
            raise argparse.ArgumentTypeError("Description must be alphanumeric")

        add_parser = sub_parser.add_parser("add", help="Add a new key to the card")
        _add_key_type_options(add_parser)
        add_parser.add_argument("description", nargs='*', default="", type=description_type,
                                help="Add a description for the entry")

    def _add_delete_sub_parser(sub_parser):
        delete_parser = sub_parser.add_parser("delete", help="Delete key from the card")
        _add_key_type_options(delete_parser)

    def _add_list_sub_parser(sub_parser):
        sub_parser.add_parser("list", help="List user keys")

    user_key_sub_parser = subparsers.add_parser(enums.Command.USER_KEY.value,
                                                help="User Key subcommand")

    action_sub_parser = user_key_sub_parser.add_subparsers(dest="subaction", required=True)

    _add_list_sub_parser(action_sub_parser)
    _add_add_sub_parser(action_sub_parser)
    _add_delete_sub_parser(action_sub_parser)


def _transfer(subparsers, interactive_mode):
    def _validate(address: str) -> str:
        try:
            int(address, 16)
        except ValueError:
            raise argparse.ArgumentTypeError("Not a valid ETH address")

        if not (address.startswith("0x") and len(address) in (40, 42)):
            raise argparse.ArgumentTypeError("Not a valid ETH address")

        return address

    sub_parser = subparsers.add_parser(enums.Command.TRANSFER.value, help="Transfer tokens")

    if interactive_mode:
        add_pin_option(sub_parser)

    sub_parser.add_argument("address", type=_validate, help="Address where to send funds")
    sub_parser.add_argument("amount", type=Decimal, help="Amount to send")
    sub_parser.add_argument("--price", type=int, help="Gas price")
    sub_parser.add_argument("--limit", type=int, help="Gas limit")


def _xpub_options(subparsers, interactive_mode):
    """
    Add xpub command options

    :param subparsers: Argument parser subparsers
    :param interactive_mode: Whether running in interactive mode
    """
    from ..get_xpub import GetXpub

    GetXpub.add_options(subparsers)


def _get_clearpubkey_options(subparsers, interactive_mode):
    """
    Add get_clearpubkey command options

    :param subparsers: Argument parser subparsers
    :param interactive_mode: Whether running in interactive mode
    """
    from ..get_clearpubkey import GetClearpubkey

    GetClearpubkey.add_options(subparsers)


def _decrypt_options(subparsers, interactive_mode):
    """
    Add decrypt command options

    :param subparsers: Argument parser subparsers
    :param interactive_mode: Whether running in interactive mode
    """
    from ..decrypt import Decrypt
    Decrypt.add_options(subparsers)


def _cert_options(subparsers, _: bool):
    """
    Add manufacturer certificate command options

    :param subparsers: Argument parser subparsers
    """
    subparsers.add_parser(enums.Command.CERTIFICATE.value,
                          help="Retrieve and display the manufacturer certificate")
