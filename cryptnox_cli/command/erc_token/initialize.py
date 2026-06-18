# -*- coding: utf-8 -*-
"""
Module for handling the initialization of ERC tokens on Cryptnox cards,
supporting ERC20, ERC721, and ERC1155 standards. It manages token metadata,
contract ABIs, and dual-card setup for enhanced security.
"""

import gzip
import json
import urllib.error
import urllib.parse
from argparse import Namespace
from typing import List

import cryptnox_sdk_py
import requests

from ..helper import ui
from ..helper.cards import ExitException, CardManager

try:
    from wallet import eth
except ImportError:
    from ...wallet import eth


class Initialize:
    def __init__(self, data: Namespace, cards: CardManager = None):
        self.data = data
        self._cards = cards or CardManager(self.data.verbose if "verbose" in self.data else False)
        self.serial_number = None

    def execute(self, card: cryptnox_sdk_py.Card) -> int:
        if card.initialized:
            print("Card already initialized.")
            return 1

        print("Cryptnox Initialisation\n")

        init_data = ui.get_init_data(card, self.data.easy_mode)
        nfc_sign = ui.confirm("Sign with NFC:")

        print("Select type of token to initialize the card with:")
        try:
            token_type = ui.option_input(
                {
                    "nft": "NFT (ERC721)",
                    "token": "Token (ERC20)",
                    "multi": "Multi token (ERC1155)"
                },
                "Token Type")
        except ExitException as error:
            print(error)
            return -1

        print(token_type)
        if token_type == "nft":
            try:
                slots = Initialize._nft_slots()
            except ValueError as error:
                print(f"Error in getting input for NFT: {error}")
                return -1
        elif token_type == "token":
            try:
                slots = Initialize._token_slots()
            except ValueError as error:
                print(f"Error in getting input for Token: {error}")
                return -1
        elif token_type == "multi":
            try:
                slots = Initialize._multi_token_slots()
            except ValueError as error:
                print(f"Error in getting input for NFT: {error}")
                return -1
        else:
            return -1

        self._init_card(card, init_data, nfc_sign, slots)

        serial_number = card.serial_number
        del self._cards[serial_number]
        card = self._cards[serial_number]

        if ui.confirm("Configure another card with same information?"):
            self._dual_seed(card, init_data, nfc_sign, slots)
        else:
            Initialize._seed(card, init_data.pin)

            print("Cards have been initialized.")
            if self.data.easy_mode:
                print("Cards are in easy mode.\n\nPress enter for all pin and puk prompts.\n")

        return 0

    def _dual_seed(self, card: cryptnox_sdk_py.Card, init_data, nfc_sign, slots: List[str]):
        serial_number = card.serial_number
        card.verify_pin(init_data.pin)
        first_pair = card.dual_seed_public_key(init_data.pin)
        index = card.connection.index
        del self._cards[index]
        input("Please, insert card pair that will be used for dual initialization and press ENTER.")
        dual_card = self._cards[index]
        while True:
            if not isinstance(dual_card, cryptnox_sdk_py.card.Nft):
                print("This card is not an NFT card")
            elif dual_card.serial_number == serial_number:
                print("This is the same card as the first check was done on.")
            elif dual_card.initialized:
                print("This card is already initialized.")
            elif dual_card.seed_source != cryptnox_sdk_py.SeedSource.NO_SEED:
                print("This card has a seed.")
            else:
                break
            del self._cards[index]
            input("Please, insert card pair that will be used for dual initialization and press ENTER.")
            dual_card = self._cards[index]

        self._init_card(dual_card, init_data, nfc_sign, slots)
        second_serial_number = dual_card.serial_number
        del self._cards[second_serial_number]
        dual_card = self._cards[second_serial_number]
        dual_card.verify_pin(init_data.pin)
        second_pair = dual_card.dual_seed_public_key(init_data.pin)
        dual_card.dual_seed_load(first_pair, init_data.pin)
        del self._cards[index]
        input(f"Please, insert card with serial number {serial_number} and press ENTER.")
        card = self._cards[serial_number]
        card.verify_pin(init_data.pin)
        card.dual_seed_load(second_pair, init_data.pin)

        print("Card has been initialized.")
        print("Use 'info' command to see all information regarding your token.")
        if self.data.easy_mode:
            print("Card is in easy mode.\n\nPress enter for all pin and puk prompts.\n")

    def _init_card(self, card: cryptnox_sdk_py.Card, init_data: ui.InitData, nfc_sign: bool,
                   slots: List[str]):
        print("\nInitializing the applet\n")
        card.init(init_data.name, init_data.email, init_data.pin, init_data.puk, nfc_sign=nfc_sign)
        serial_number = card.serial_number

        del self._cards[serial_number]
        card = self._cards[serial_number]
        card.verify_pin(init_data.pin)

        print("Writing data...")
        for index, value in enumerate(slots):
            if value:
                card.user_data[index] = gzip.compress(value.encode("UTF8"))
        print("Data written")

    @staticmethod
    def _nft_slots() -> List[str]:
        print("-------------------------------------------------")
        print("\n\nNFT data")
        print("-------------------------------------------------")
        endpoint = ui.input_with_exit("Endpoint URL: ").lower()
        chain_id = ui.input_type("Chain ID: ", type_of_input=int)
        contract_address = ui.input_with_exit("Contract address: ")
        nft_id = ui.input_with_exit("NFT ID: ")
        return [
            json.dumps({
                "endpoint": endpoint,
                "chain_id": chain_id,
                "contract_address": contract_address,
                "nft_id": nft_id,
            }),
            "",
            Initialize._abi(),
            ui.input_with_exit("Metadata: ")
        ]

    @staticmethod
    def _seed(card: cryptnox_sdk_py.Card, pin_code: str) -> None:
        print("Generating seed...")
        card.generate_seed(pin_code)
        print("Seed generated")
        public_key = card.get_public_key()
        address = eth.checksum_address(public_key)
        ui.print_warning(f"Your address is: {address}"
                         f"\nTransfer tokens to it to complete the initialization process.")

    @staticmethod
    def _token_slots() -> list[str]:
        print("-------------------------------------------------")
        print("\n\nToken data")
        print("-------------------------------------------------")
        endpoint = ui.input_with_exit("Endpoint URL: ").lower()
        chain_id = ui.input_type("Chain ID: ", type_of_input=int)
        contract_address = ui.input_with_exit("Contract address: ")

        return [
            json.dumps({
                "erc": 20,
                "endpoint": endpoint,
                "chain_id": chain_id,
                "contract_address": contract_address,
            })
        ]

    @staticmethod
    def _abi() -> str:
        def uri_validator(x):
            try:
                result = urllib.parse.urlparse(x)
                return all([result.scheme, result.netloc])
            except Exception:
                return False

        abi = ui.input_with_exit("ABI: ")

        if uri_validator(abi):
            return Initialize._get_abi_from_url(abi)
        try:
            int(abi)
        except ValueError:
            try:
                json.loads(abi)
            except json.JSONDecodeError:
                raise ValueError("Invalid abi")

        return abi

    @staticmethod
    def _get_abi_from_url(url):
        try:
            data_request = requests.get(url)
        except urllib.error.URLError as error:
            raise ValueError(f"Error in retrieving {url}: {error}") from error

        try:
            data = data_request.json()
        except json.JSONDecodeError as error:
            raise ValueError("Error in decoding ABI url response") from error

        if data.get('status') != '1':
            raise ValueError(f"Error in retrieving ABI url response: {data.get('message')}")

        return data_request.text

    @staticmethod
    def _multi_token_slots():
        print("-------------------------------------------------")
        print("\n\nMulti token data")
        print("-------------------------------------------------")
        endpoint = ui.input_with_exit("Endpoint URL: ").lower()
        chain_id = ui.input_type("Chain ID: ", type_of_input=int)
        contract_address = ui.input_with_exit("Contract address: ")
        token_id = ui.input_with_exit("NFT ID: ")
        return [
            json.dumps({
                "erc": 1155,
                "endpoint": endpoint,
                "chain_id": chain_id,
                "contract_address": contract_address,
                "token_id": token_id,
            }),
            "",
            Initialize._abi(),
            ui.input_with_exit("Metadata: ")
        ]
