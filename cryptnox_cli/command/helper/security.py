# -*- coding: utf-8 -*-
"""
Module dealing with security of the application.
"""
import typing
from typing import List, Dict

import cryptnox_sdk_py

from .. import user_keys


class ExitException(Exception):
    """Raised when user has indicated he want's to exit the command"""


def _secret_with_exit(text, required=True):
    """
    Local implementation of secret_with_exit to avoid circular import.
    Replicates the functionality of ui.secret_with_exit.
    """
    from stdiomask import getpass

    while True:
        value = getpass(text).strip()
        if value.lower() == "exit":
            raise ExitException
        if required and not value:
            print("This entry is required")
        else:
            break

    return value


class Unauthorized(Exception):
    """
    None of the authorization methods has validated the user.
    """


EASY_MODE_PIN = "000000000"
EASY_MODE_TEXT = "easy mode"


def easy_mode_puk(card):
    return "0" * card.PUK_LENGTH


def check(card, check_seed: bool = True) -> bool:
    """
    Check if card is initialized and pin code is saved.

    :param Card card: Card to use
    :param bool check_seed: If True checks if seed is generated
    :return:
    """
    if card.open:
        return True

    card.check_init()

    if not card.valid_key and check_seed:
        raise cryptnox_sdk_py.exceptions.SeedException("The key is not generated")

    result = False
    try:
        result = user_keys.authenticate(card)
    except NotImplementedError:
        pass

    if not result:
        if card.pin_authentication:
            result = bool(check_pin_code(card))
        else:
            raise Unauthorized("PIN authentication is not allowed.")

    return result


def check_pin_code(card, text: str = "Cryptnox PIN code: ") -> str:
    """
    Check PIN code entered by user against the card on given connection.

    :param Base card: Card to use
    :param str text: Prompt to show to the user

    :return: The entered valid pin code
    :rtype: str
    """

    authorized = False
    pin_code = "1"
    easy_mode = is_easy_mode(card.info)

    while not authorized:
        if easy_mode:
            print(f"Card is in {EASY_MODE_TEXT}. Using easy mode PIN automatically.")
            pin_code = EASY_MODE_PIN
        else:
            try:
                retries = card.verify_pin(None)
                if retries is not None:
                    if retries == 0:
                        raise cryptnox_sdk_py.exceptions.PinBlockedException(
                            "PIN is locked. Use your PUK to unlock the card."
                        )
                    try_str = "attempt" if retries == 1 else "attempts"
                    prompt_text = f"Cryptnox PIN code ({retries} {try_str} remaining): "
                else:
                    prompt_text = text
            except cryptnox_sdk_py.exceptions.PinBlockedException:
                raise
            except cryptnox_sdk_py.exceptions.PinException:
                print("Card requires a power cycle. Please remove and re-tap the card, then try again.")
                raise
            except Exception:
                prompt_text = text

            pin_code = get_pin_code(card, prompt_text)

        try:
            authorized = _check_pin_code(card, pin_code, not easy_mode)
        except cryptnox_sdk_py.exceptions.PinException:
            if easy_mode:
                print(f"{EASY_MODE_TEXT} PIN doesn't work. Try other PIN code.\n")
                easy_mode = False
            else:
                raise
        except (cryptnox_sdk_py.exceptions.PinAuthenticationException,
                cryptnox_sdk_py.exceptions.SoftLock):
            print("Card requires a power cycle. Please remove and re-tap the card, then try again.")
            raise

    return pin_code


def get_pin_code(card: cryptnox_sdk_py.Card, text: str = "Enter PIN code:",
                 allowed_values: List[str] = None) -> str:
    """
    Get PIN code from the user according to the rules.

    :param Card card: Card to use for PIN code check
    :param str text: Prompt to show to the user
    :param List[str] allowed_values: Valid values besides the those defined
                                     in the rules
    :return: PIN code entered by the user
    :rtype: str
    """
    return _get_code(card.valid_pin, text, allowed_values)


def is_easy_mode(card_info: Dict):
    try:
        return card_info["name"] == card_info["email"] == EASY_MODE_TEXT.upper()
    except TypeError:
        return False


def process_command_with_puk(
        card: cryptnox_sdk_py.Card,
        function: typing.Callable,
        *args,
        **kwargs) -> bool:
    easy_mode = is_easy_mode(card.info)

    while True:
        if easy_mode:
            print(f"Card is in {EASY_MODE_TEXT}. Using easy mode PUK automatically.")

        if easy_mode:
            puk_code = easy_mode_puk(card)
        else:
            puk_code = get_puk_code(card)

        try:
            result = function(*args, **kwargs, puk=puk_code)
        except cryptnox_sdk_py.exceptions.PukException as error:
            if easy_mode:
                print(f"{EASY_MODE_TEXT} PUK doesn't work. Try other PUK code.\n")
                easy_mode = False
            else:
                if error.number_of_retries > 0:
                    print(f"Wrong PUK code. Remaining retries: {error.number_of_retries} "
                          f"Try again.")
                else:
                    raise
        else:
            break

    return result


def _check_pin_code(card, pin_code, handle_exception: bool = True) -> bool:
    try:
        card.verify_pin(str(pin_code))
    except cryptnox_sdk_py.exceptions.PinException as error:
        if not handle_exception:
            raise error
        number_of_retries = error.number_of_retries
        print("Wrong PIN code.")
        if number_of_retries == 0:
            print("PIN is locked. Use your PUK to unlock the card.")
            raise
        try_str = "attempt" if number_of_retries == 1 else "attempts"
        print(f"{number_of_retries} {try_str} remaining before the card is locked.")

        return False

    return True


def get_puk_code(card: cryptnox_sdk_py.Card, text: str = "", allowed_values: List = None) -> str:
    """
    Get user input for puk code and check if it is valid.

    :param Card card: Card for use to check PUK code validity
    :param str text: Text displayed to user for value input.
    :param List allowed_values: Values other than 15 digits long strings
        that can be accepted.
    :return: Entered puk code.
    :rtype: str
    """
    text = text or f"Enter the PUK ({card.puk_rule}): "
    return _get_code(card.valid_puk, text, allowed_values)


def _get_code(
        validation_method: typing.Callable,
        text: str = "",
        allowed_values: List = None) -> str:
    allowed_values = allowed_values or []
    code = _secret_with_exit(text, required=("" not in allowed_values))

    if not {code, ""}.isdisjoint(allowed_values):
        return code

    while True:
        try:
            validation_method(code)
        except cryptnox_sdk_py.exceptions.DataValidationException as error:
            print(error, "\n")
            code = _secret_with_exit(text, required=("" not in allowed_values))

            if code in allowed_values:
                break
        else:
            break

    return code
