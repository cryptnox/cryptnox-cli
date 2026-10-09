# -*- coding: utf-8 -*-
"""
Module for displaying comprehensive information about ERC tokens stored
on the Cryptnox card, including token balances, ownership verification,
metadata display, and dual-card validation for enhanced security.
"""

import gzip
import json
import secrets
from pathlib import Path

import cryptnox_sdk_py
import cryptography.exceptions
from argparse import Namespace
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from eth_typing import ChecksumAddress
from tabulate import tabulate

from ..cards import Cards
from ..helper.cards import CardManager

__all__ = ['Cards']

try:
    from ... import enums
    from ...wallet import eth
except ImportError:
    import enums
    from wallet import eth

_SEED_SOURCE_TRANSLATION = {
    cryptnox_sdk_py.SeedSource.NO_SEED: "No seed",
    cryptnox_sdk_py.SeedSource.INTERNAL: "Single card",
    cryptnox_sdk_py.SeedSource.DUAL: "Dual card",
}

_ERC_PATH = Path(__file__).parent.parent.parent.joinpath("contract_abi")


def _erc_abi_file(value):
    return _ERC_PATH.joinpath(f"erc{value}.json").absolute()


class Info:
    """
    Command to show information about accounts connected to the card
    """
    _name = enums.Command.INFO.value

    def __init__(self, data: Namespace, cards: CardManager = None):
        self.data = data
        self._cards = cards or CardManager(self.data.verbose if "verbose" in self.data else False)
        self.serial_number = None

    def execute(self, card: cryptnox_sdk_py.Card) -> int:
        slots = []
        for i in range(0, 4):
            slots.append(gzip.decompress(card.user_data[i]))

        slot0 = json.loads(slots[0].decode("UTF8"))
        if "erc" in slot0:
            with open(_erc_abi_file(slot0["erc"])) as f:
                abi = f.read()
        else:
            abi = slots[2].decode("UTF8")
        endpoint = slot0['endpoint']

        print("----------------------------------------------")
        seed_source = card.seed_source
        print(_SEED_SOURCE_TRANSLATION[seed_source])
        print("----------------------------------------------")
        public_key = card.get_public_key()
        print(f"Public key: {public_key}")
        print("----------------------------------------------")
        Info._private_key_check(card, bytes.fromhex(public_key))
        print("----------------------------------------------")
        Info._history_counter(card)
        print("----------------------------------------------")
        address = eth.checksum_address(public_key)
        print(f"Address: {address}")
        print("----------------------------------------------")

        if "erc" not in slot0:
            Info._owner(endpoint, slot0['contract_address'], abi, address, slot0['nft_id'])
            print("----------------------------------------------\n\n")
        elif slot0['erc'] == 1155:
            Info._owner(endpoint, slot0['contract_address'], abi, address, slot0['token_id'])
            print("----------------------------------------------\n\n")

        if seed_source == cryptnox_sdk_py.SeedSource.DUAL:
            index = card.connection.index
            serial_number = card.serial_number
            del self._cards[index]
            input("Please, insert card pair that was used for dual initialization and press ENTER.")
            card = self._cards[index]
            while True:
                if not isinstance(card, cryptnox_sdk_py.card.Nft):
                    print("This card is not an NFT card")
                elif card.seed_source != cryptnox_sdk_py.SeedSource.DUAL:
                    print("This card is not dual initialized")
                elif card.serial_number == serial_number:
                    print("This is the same card as the first check was done on.")
                else:
                    break
                del self._cards[index]
                input("Please, insert card pair that was used for dual initialization.")
                card = self._cards[index]

            print("----------------------------------------------")
            print("Checking second card public key is same as public key from first card...")
            second_card_public_key = card.get_public_key()
            print("OK" if second_card_public_key != public_key else "FAILED! The public keys differ")
            print("----------------------------------------------")
            Info._private_key_check(card, bytes.fromhex(second_card_public_key))
            print("----------------------------------------------")
            Info._history_counter(card)
            print("----------------------------------------------")
            same = True
            for index, slot in enumerate(slots):
                if gzip.decompress(card.user_data[index]) != slot:
                    same = False
                    break
            if same:
                print("Card user data same on both cards.")
            else:
                print("Card user data not the same on both cards")
            print("----------------------------------------------")

        print("\n\n")
        Info._balance(endpoint, address)
        print("----------------------------------------------")
        print(f"Endpoint: {slot0['endpoint']}")
        print("----------------------------------------------")
        print(f"Chain ID: {slot0['chain_id']}")
        print("----------------------------------------------")
        print(f"Contract address: {slot0['contract_address']}")
        print("----------------------------------------------")

        try:
            erc = slot0['erc']
        except KeyError:
            erc = 721

        if erc == 20:
            Info._token_balance(endpoint, slot0['contract_address'], abi, address)
        elif erc in (721, 1155):
            print(f"Token ID: {slot0['nft_id' if erc == 721 else 'token_id']}")
            print("----------------------------------------------")
            metadata = slots[3].decode("UTF8").replace("\n", "")
            print(f"metadata: {metadata}")
            print("----------------------------------------------")
            Info._url(metadata)

        return 0

    @staticmethod
    def _balance(endpoint, address):
        from web3 import Web3

        try:
            w3 = Web3(Web3.HTTPProvider(endpoint))
            print(f"Balance: {Web3.from_wei(w3.eth.get_balance(address), 'ether')} ETH")
        except Exception as error:
            print(f"Error getting balance: {error}")

    @staticmethod
    def _history_counter(card: cryptnox_sdk_py.Card):
        print("Checking signature counter and history...")
        signature_counter = card.signing_counter
        history = []
        index = 0
        entry = card.history(index)
        while entry.signing_counter != 0:
            history.append([entry.signing_counter, entry.hashed_data.hex()])
            index += 1
            entry = card.history(index)
        print(f"Signature counter: {signature_counter}")
        if history:
            print(tabulate(history))
        else:
            print("No history entries.")

    @staticmethod
    def _private_key_check(card: cryptnox_sdk_py.Card, public_key: bytes):
        print("Checking private key on the card...")

        nonce = secrets.token_bytes(nbytes=16)
        signature_check = card.signature_check(nonce)
        if signature_check.message[2:18] != nonce:
            print("FAILED!\nPublic and private key differ")
            return

        try:
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key)
        except ValueError:
            print("FAILED!\nInvalid public key")
            return

        try:
            public_key.verify(signature_check.signature, signature_check.message,
                              ec.ECDSA(hashes.SHA256()))
        except cryptography.exceptions.InvalidSignature:
            print("FAILED!\nPublic and private key differ")
        else:
            print("OK")

    @staticmethod
    def _owner(
            endpoint: str,
            contract_address: ChecksumAddress,
            abi: str,
            account: str,
            token_id: int) -> None:
        from web3 import Web3

        print(f"Checking owner on contract: {contract_address}...")
        w3 = Web3(Web3.HTTPProvider(endpoint))
        try:
            contract = w3.eth.contract(address=contract_address, abi=abi)
        except ValueError:
            print("ABI format is not json")
            return

        function = contract.get_function_by_name("balanceOf")
        try:
            if function(account, int(token_id)).call() == 1:
                print("OK")
            else:
                print(f"FAILED\nThe Token doesn't belong to address: {account}")
        except Exception:
            print("FAILED!\nIssue with checking ownership")

    @staticmethod
    def _token_balance(endpoint: str, contract_address: ChecksumAddress, abi: str,
                       account: str) -> None:
        from web3 import Web3

        print(f"Checking token on contract: {contract_address}...")
        w3 = Web3(Web3.HTTPProvider(endpoint))
        try:
            contract = w3.eth.contract(address=contract_address, abi=abi)
        except ValueError:
            print("ABI format is not json")
            return

        try:
            name = contract.get_function_by_name("name")().call()
            balance = contract.get_function_by_name("balanceOf")(account, 1).call()
            symbol = contract.get_function_by_name("symbol")().call()
        except Exception as error:
            print(f"FAILED!\nIssue with checking ownership: {error}")
        else:
            print(f"Contract name: {name}")
            print(f"Balance: {balance} {symbol}")

    @staticmethod
    def _url(metadata) -> None:
        try:
            metadata_json = json.loads(metadata)
        except json.decoder.JSONDecodeError:
            print("Error parsing metadata")
            return
        else:
            try:
                print(metadata_json['image'])
            except KeyError:
                try:
                    print(f"https://ipfs.io/ipfs/{metadata_json['image_url'].split('//')[1]}")
                except (KeyError, IndexError):
                    print("Can't find image")
