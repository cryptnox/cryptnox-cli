# -*- coding: utf-8 -*-
"""
Module containing abstract class for creating command child classes
"""
import abc

import cryptnox_sdk_py
import requests.exceptions
from argparse import Namespace
from tabulate import tabulate

from .helper import (
    ui, security
)
from .helper.cards import (
    CardManager,
    ExitException,
    TimeoutException,
)
from .helper.security import (
    check,
    Unauthorized
)


class Command(metaclass=abc.ABCMeta):
    """
    Base class for all commands

    :param Namespace data: Command line arguments
    """

    def __init__(self, data: Namespace, cards: CardManager = None):
        self.data = data
        self._cards = cards or CardManager(self.data.verbose if "verbose" in self.data else False)
        self.serial_number = None

    def execute(self, serial_number: int = None) -> int:
        """
        Main execution method of the command.

        Finds card and establishes connection to it. Executes _execute method.

        :param serial_number: Serial number of the wanted card
        :return: 0 if the command executed without issues. Other number
                 indicating and issue
        :rtype: int
        """
        result = self._handle_execution(serial_number)

        return result

    def _handle_execution(self, serial_number: int = None) -> int:
        self.serial_number = serial_number
        try:
            self.serial_number = self.data.serial
        except AttributeError:
            pass
        try:
            card = self._cards[self.serial_number]
        except (ExitException, TimeoutException, cryptnox_sdk_py.exceptions.CryptnoxException) as error:
            print(error)
            return -1
        except requests.exceptions.RequestException as error:
            print(f"Error in retrieving information: {error}")
            return -1

        self.run_execute(card)

    def run_execute(self, card) -> int:
        print(f"Using card with serial number {card.serial_number}")
        origin = card.origin
        if origin == cryptnox_sdk_py.enums.Origin.UNKNOWN:
            ui.print_warning("Origin of card can't be checked. Check your internet connection.")
        elif origin == cryptnox_sdk_py.enums.Origin.FAKE:
            ui.print_warning(f"Card with serial number {card.serial_number} is not genuine.")

        try:
            result = self._execute(card)
        except cryptnox_sdk_py.exceptions.InitializationException as error:
            print("\n" + tabulate([[str(error).upper()]],
                                  tablefmt="rst"))
            print(f"To initialize card run : init\n"
                  f"To initialize card in {security.EASY_MODE_TEXT} run : init -e")
            result = -1
        except cryptnox_sdk_py.exceptions.SeedException:
            print("The seed is not generated\nRun seed command to generate seed")
            result = -1
        except cryptnox_sdk_py.exceptions.GenericException as error:
            print(f"Generic exception with status code: 0x{error.status.hex().upper()}")
            return -2
        except (cryptnox_sdk_py.exceptions.PinException,
                cryptnox_sdk_py.exceptions.PinAuthenticationException):
            result = -1
        except cryptnox_sdk_py.exceptions.PinBlockedException as error:
            print(error)
            result = -1
        except (cryptnox_sdk_py.exceptions.CryptnoxException, NotImplementedError) as error:
            print(error)
            result = -1
        except ui.ExitException:
            print("Exited by user.")
            result = -1
        except Unauthorized as error:
            print(error)
            print("User not authorized")
            result = -2

        return result

    @property
    @abc.abstractmethod
    def _name(self):
        pass

    @abc.abstractmethod
    def _execute(self, card) -> int:
        """
        Method that will be executed in executed in execute method.

        :param connection cryptnox_sdk_py.Connection: Connection to the card
        :return: Execution status
        """

    @classmethod
    def meets_condition(cls, data: Namespace) -> bool:
        """
        Take responsibility for command line arguments for processing.

        :param Namespace data: Command line arguments given by user

        :return: Whether this class can handle the user request
        :rtype: bool
        """
        return data.command == cls._name

    @classmethod
    def __subclasshook__(cls, c):
        if cls is Command:
            attrs = set(dir(c))

            if set(cls.__abstractmethods__) <= attrs:
                return True

        return NotImplemented

    @staticmethod
    def _check(card, check_seed: bool = True) -> bool:
        """
        Check if card is initialized and pin code is saved.

        :param Card card: Card to use
        :param bool check_seed: If True checks if seed is generated
        :return:
        """
        return check(card, check_seed)
