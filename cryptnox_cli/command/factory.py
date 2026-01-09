# -*- coding: utf-8 -*-
"""
Module for creating Factory class.
"""
import importlib
from argparse import Namespace

from .command import Command
from .helper.cards import CardManager
from .unknown import Unknown


def command(data: Namespace, cards: CardManager = None) -> Command:
    """
    Gives back the command that took responsibility for executing the
    command

    :param Namespace data: Command line arguments and options
    :param Cards cards: List of cards to use for the command
    :param int card_type: Card type to work with

    :return: Command that can execute the given user input
    :rtype: Command
    """
    # Dynamically import all command modules to register them with Command.__subclasses__()
    command_modules = [
        'btc', 'card_configuration', 'change_pin', 'change_puk', 'config',
        'eth', 'history', 'info', 'initialize', 'seed', 'cards', 'server',
        'reset', 'unlock_pin', 'user_key', 'transfer', 'get_xpub',
        'get_clearpubkey', 'decrypt', 'manufacturer_certificate'
    ]

    for module_name in command_modules:
        try:
            importlib.import_module(f'.{module_name}', package=__package__)
        except ImportError as e:
            raise ImportError(f"Required command module '{module_name}' could not be imported: {e}")

    for cls in Command.__subclasses__():
        if cls.meets_condition(data):
            return cls(data, cards)

    return Unknown(data)
