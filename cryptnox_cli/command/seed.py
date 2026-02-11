# -*- coding: utf-8 -*-
"""
Module containing command for generating keys on the card
"""

import cryptnox_sdk_py

from . import user_keys
from .command import Command
from .helper import (
    cards,
    security,
    ui
)

try:
    import enums
    from lib import cryptos
except ImportError:
    from .. import enums
    from ..lib import cryptos


class Seed(Command):
    """
    Command to generate keys on the card
    """
    _name = enums.Command.SEED.value

    def _execute(self, card) -> int:
        if card.type != ord("B"):
            print("Method not supported with this card type.")
            return 0

        card.check_init()

        if card.valid_key:
            print("\nKey is already generated"
                  "\nReset the card before generating another one")
            return 0

        actions = {
            "chip": Seed._chip,
            "dual": self._dual_seed,
            "recover": Seed._recover,
            "upload": Seed._upload,
        }

        try:
            result = actions[self.data.action](card)
        except KeyError:
            print("Method not supported with this card type.")
            result = 1

        return result

    @staticmethod
    def _chip(card: cryptnox_sdk_py.Card) -> int:
        """
        Generate seed directly in the card's secure chip.

        Note: This method generates the seed entirely on the card's hardware and does not
        use BIP39 mnemonics. Therefore, BIP39 passphrases do not apply to this seed
        generation method. The seed cannot be exported or backed up as a mnemonic phrase.

        :param card: The Cryptnox card
        :return: 0 on success
        """
        pin_code = Seed._get_pin_code(card)

        print("Generating seed directly in card's secure chip...")
        print("Note: This seed is generated on-chip and does not use BIP39 mnemonics.")
        print("BIP39 passphrases do not apply to this generation method.")
        print()

        card.generate_seed(pin_code)
        print("New key generated in card.")

        return 0

    def _dual_seed(self, card: cryptnox_sdk_py.Card) -> int:
        """
        Generate the same seed on two cards using secure dual-card generation.

        Note: This method generates seeds using a secure two-card protocol and does not
        use BIP39 mnemonics. Therefore, BIP39 passphrases do not apply to this seed
        generation method. The seed is generated securely on both cards and never leaves
        the hardware.

        :param card: The first Cryptnox card
        :return: 0 on success, -1 or -2 on error
        """
        try:
            card.dual_seed_public_key()
        except NotImplementedError as error:
            print(error)
            return -1
        except cryptnox_sdk_py.exceptions.DataValidationException:
            pass

        print("Dual seed generation process starting...")
        print("Note: This method uses secure on-chip generation and does not use BIP39 mnemonics.")
        print("BIP39 passphrases do not apply to this generation method.")
        print()

        pin_code = Seed._get_pin_code(card)

        serial_number = card.serial_number
        index = card.connection.index
        first_card_data = card.dual_seed_public_key(pin_code)

        del self._cards[serial_number]

        print(f"Remove card with serial number {serial_number} (first card) and insert the second "
              f"card into same reader with index {index}.")
        input("Insert card and press ENTER to continue")

        try:
            second_card = self._get_second_card(index, serial_number)
        except (cards.ExitException, cards.TimeoutException) as error:
            print(error)
            return -2

        pin_code = Seed._get_pin_code(second_card)
        second_card_data = second_card.dual_seed_public_key(pin_code)
        second_card.dual_seed_load(first_card_data, pin_code)
        print(f"Remove card with serial number {second_card.serial_number} (second card) and "
              f"insert the card with serial number {serial_number} (first card) into the same "
              f"reader with index {index}.")
        input("Insert card and press ENTER to continue")
        del self._cards[card.serial_number]

        try:
            card = self._cards[serial_number]
        except (cards.ExitException, cards.TimeoutException) as error:
            print(error)
            print("First card seed has been generated. Reset it before doing dual seed generation "
                  "again.")
            return -2

        pin_code = Seed._get_pin_code(card)
        card.dual_seed_load(second_card_data, pin_code)
        print("Dual seed generation has been finished. Check with command `info` that both of them "
              "have the same addresses.")
        del self._cards[serial_number]

        return 0

    @staticmethod
    def _get_pin_code(card: cryptnox_sdk_py.Card) -> str:
        card.check_init()

        pin_code = ""
        if not card.open:
            try:
                if not user_keys.authenticate(card):
                    pin_code = security.check_pin_code(card)
            except NotImplementedError:
                pin_code = security.check_pin_code(card)
        elif card.auth_type == cryptnox_sdk_py.AuthType.PIN:
            pin_code = security.check_pin_code(card)

        return pin_code

    def _get_second_card(self, index: int, first_card_serial_number: int) -> cryptnox_sdk_py.Card:
        while True:
            card = self._cards[index]
            if not card.initialized:
                print(f"This card, serial number {card.serial_number} is not "
                      f"initialized. Insert another card.")
                input("Press ENTER to continue.")
            if card.serial_number == first_card_serial_number:
                print(f"Please replace card with another one. First card with serial number "
                      f"{first_card_serial_number} detected.")
                input("Press ENTER to continue.")
            elif card.valid_key:
                print("\nThis card already has a seed. Insert another card or reset this one.")
                input("Press ENTER to continue.")
            else:
                try:
                    card.dual_seed_public_key()
                except NotImplementedError:
                    print(f"Second card, {card.serial_number} doesn't have this functionality. "
                          f"Insert another card")
                    input("Press ENTER to continue.")
                except cryptnox_sdk_py.exceptions.DataValidationException:
                    break
                else:
                    break

        return card

    @staticmethod
    def _load_mnemonic(card: cryptnox_sdk_py.Card, mnemonic: str, pin_code: str,
                       passphrase: str = '') -> None:
        """
        Load mnemonic onto card with optional BIP39 passphrase.

        :param card: The Cryptnox card
        :param mnemonic: The BIP39 mnemonic phrase (12 or 24 words)
        :param pin_code: The card PIN code
        :param passphrase: Optional BIP39 passphrase (13th/25th word)
        """
        if len(mnemonic.split(' ')) not in (12, 24):
            raise ValueError('Only mnemonic passphrases of length 12 and 24 are supported')
        seed = cryptos.bip39_mnemonic_to_seed(mnemonic, passphrase=passphrase)
        card.load_seed(seed, pin_code)

    @staticmethod
    def _recover(card: cryptnox_sdk_py.Card) -> int:
        """
        Recover wallet from BIP39 mnemonic phrase with optional passphrase.

        :param card: The Cryptnox card
        :return: 0 on success, -1 on error
        """
        pin_code = Seed._get_pin_code(card)

        print("\nEnter the mnemonic root to recover (12 or 24 words):")
        mnemonic = ui.input_with_exit("> ")

        try:
            passphrase = ui.get_bip39_passphrase(confirm_required=True)
        except ui.ExitException as error:
            print(error)
            return -1

        try:
            Seed._load_mnemonic(card, mnemonic, pin_code, passphrase=passphrase)
        except Exception as error:
            print(error)
            return -1

        print("Mnemonic loaded, please keep it safe for backup.")
        if passphrase:
            print("You MUST use the same passphrase when restoring this wallet.")

        return 0

    @staticmethod
    def _upload(card: cryptnox_sdk_py.Card) -> int:
        """
        Generate new seed, optionally with BIP39 passphrase, and upload to card.

        :param card: The Cryptnox card
        :return: 0 on success, -1 on error
        """
        pin_code = Seed._get_pin_code(card)
        seed = card.generate_random_number(32)
        mnemonic = cryptos.entropy_to_words(seed)

        try:
            passphrase = ui.get_bip39_passphrase(confirm_required=True)
        except ui.ExitException as error:
            print(error)
            return -1

        try:
            Seed._load_mnemonic(card, mnemonic, pin_code, passphrase=passphrase)
        except Exception as error:
            print(error)
            return -1

        # Security: Prompt before displaying sensitive mnemonic
        ui.print_warning("SECURITY WARNING: Mnemonic Recovery Phrase")
        print("The mnemonic phrase is highly sensitive. Anyone with access to it can control your wallet.")
        print("Ensure:")
        print("  - No one is looking at your screen")
        print("  - Screen recording/sharing is disabled")
        print("  - Terminal logging is disabled")

        confirm = input("\nType 'SHOW' to display the mnemonic phrase: ").strip()

        if confirm == 'SHOW':
            print("\nMnemonic root :")
            print(mnemonic)
            print("\nMnemonic loaded, please save this root mnemonic for backup.")
        else:
            print("\nMnemonic display cancelled. The seed has been loaded to the card.")

        if passphrase:
            print()
            ui.print_warning("IMPORTANT: BIP39 PASSPHRASE IN USE")
            print("You are using a BIP39 passphrase with this wallet.")
            print("To restore this wallet, you will need BOTH:")
            print("  1. The mnemonic phrase shown above")
            print("  2. Your BIP39 passphrase")
            print()
            print("Store your passphrase separately and securely!")
            print("Without the exact passphrase, you CANNOT access your funds.")

        return 0
