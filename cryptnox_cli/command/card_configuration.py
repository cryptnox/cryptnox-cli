# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module containing the class for printing card configuration
"""
import cryptnox_sdk_py
from tabulate import tabulate

from .command import Command
from .helper import security

try:
    import enums
except ImportError:
    from .. import enums


class CardConfiguration(Command):
    """
    Command for printing card configuraton
    """
    _SEED_SOURCE_TO_STRING = {
        cryptnox_sdk_py.SeedSource.NO_SEED: "No seed",
        cryptnox_sdk_py.SeedSource.SINGLE: "Single 256K1 EC pair",
        cryptnox_sdk_py.SeedSource.EXTENDED: "Extended 256K1 EC pair BIP32 node",
        cryptnox_sdk_py.SeedSource.EXTERNAL: "Externally generated",
        cryptnox_sdk_py.SeedSource.INTERNAL: "Internally generated",
        cryptnox_sdk_py.SeedSource.DUAL: "Dual initialized"
    }
    _name = enums.Command.CARD_CONFIGURATION.value

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        if self.data.value:
            if self.data.key == "pinless":
                path = "m/43'/60'/1581'" if CardConfiguration._str_to_bool(self.data.value) else ""
                security.process_command_with_puk(card, card.set_pinless_path, path=path)
                param = "PIN-less path"
            else:
                security.process_command_with_puk(card, card.set_pin_authentication,
                                                  CardConfiguration._str_to_bool(self.data.value))
                param = "PIN code authentication"
            print(f"Value for {param} changed to {self.data.value}")
            return 0

        if self.data.key:
            print("To change value use argument yes/no")
            if self.data.key == "pinless":
                print(f"PIN-less path {CardConfiguration._bool_to_str(card.pinless_enabled)}")
            else:
                print(f"PIN code authentication "
                      f"{CardConfiguration._bool_to_str(card.pin_authentication)}")
            return 0

        return CardConfiguration.show(card)

    @staticmethod
    def show(card: cryptnox_sdk_py.Card) -> int:
        data = [
            ["Card initialisation", CardConfiguration._bool_to_str(card.initialized)]
        ]
        try:
            data += [["Seed source", CardConfiguration._SEED_SOURCE_TO_STRING[card.seed_source]]]
        except NotImplementedError:
            data += [["Seed source", CardConfiguration._bool_to_str(card.valid_key)]]

        data += [
            ["PIN code authentication", CardConfiguration._bool_to_str(card.pin_authentication)],
            ["PIN-less path", CardConfiguration._bool_to_str(card.pinless_enabled)],
            ["Extended public key", CardConfiguration._bool_to_str(card.extended_public_key)],
        ]
        try:
            data += [
                ["RSA 2048 user key",
                 CardConfiguration._bool_to_str(
                     card.user_key_enabled(cryptnox_sdk_py.SlotIndex.RSA))],
                ["ECC 256 user key",
                 CardConfiguration._bool_to_str(card.user_key_enabled(cryptnox_sdk_py.SlotIndex.EC256R1))],
                ["FIDO2 user key",
                 CardConfiguration._bool_to_str(
                     card.user_key_enabled(cryptnox_sdk_py.SlotIndex.FIDO))]
            ]
        except NotImplementedError:
            data += [["User keys", "Not available"]]

        print(tabulate(data, tablefmt="plain"))

        return 0

    @staticmethod
    def _bool_to_str(value: bool) -> str:
        return "yes" if value else "no"

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        return value == "yes"
