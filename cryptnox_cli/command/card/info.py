# -*- coding: utf-8 -*-
"""
Module containing command for getting information about the card
"""
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

import cryptnox_sdk_py
import web3
from argparse import Namespace
from tabulate import tabulate

from ..cards import Cards
from ..helper.cards import CardManager
from ..helper.security import (
    check,
    is_easy_mode
)

try:
    from ... import enums
    from ...config import get_configuration
    from ...wallet import eth
    from ...wallet.btc import BTCwallet, BlkHubApi
    from ...wallet import xrp as xrp_wallet
except ImportError:
    import enums
    from config import get_configuration
    from wallet import eth
    from wallet.btc import BTCwallet, BlkHubApi
    from wallet import xrp as xrp_wallet

__all__ = ['Cards']


class Info:
    def __init__(self, data: Namespace, cards: CardManager = None):
        self.data = data
        self._cards = cards or CardManager(self.data.verbose if "verbose" in self.data else False)
        self.serial_number = None

    @staticmethod
    def execute(card) -> int:
        check(card)
        print("Gathering information from the network...")

        # Warm config cache before spawning threads (avoids card.user_data access in threads)
        get_configuration(card)

        # Phase 1: fetch all public keys sequentially (card communication is not thread-safe)
        btc_pubkey = Info._fetch_btc_pubkey(card)
        eth_pubkey = Info._fetch_eth_pubkey(card)
        xrp_pubkey = Info._fetch_xrp_pubkey(card)
        # BNB uses the same derivation path and key as ETH

        # Phase 2: query all network balances in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_btc = executor.submit(Info._get_btc_info, card, btc_pubkey)
            f_eth = executor.submit(Info._get_eth_info, card, eth_pubkey)
            f_xrp = executor.submit(Info._get_xrp_info, xrp_pubkey)
            f_bnb = executor.submit(Info._get_bnb_info, eth_pubkey)

        eth_info = f_eth.result()
        Info._print_info_table([f_btc.result(), eth_info, f_xrp.result(), f_bnb.result()])

        config = get_configuration(card)
        if not config["eth"]["api_key"] and config["eth"]["endpoint"] == "infura":
            print("\nTo use the Ethereum network with Infura. Go to https://infura.io. "
                  "Register (free) and get an API key. Set the API key with: eth config api_key")
        if is_easy_mode(card.info) and eth_info.get("balance") == "0.0 ETH":
            print("\nTo get some Sepolia testnet ETH, use a faucet like: "
                  "https://sepoliafaucet.com or https://www.alchemy.com/faucets/ethereum-sepolia")

        return 0

    @staticmethod
    def _fetch_btc_pubkey(card):
        config = get_configuration(card)["btc"]
        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]].value
        except KeyError:
            return None
        path = b"" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else BTCwallet.PATH
        try:
            return card.get_public_key(derivation, path=path)
        except Exception:
            return None

    @staticmethod
    def _fetch_eth_pubkey(card):
        config = get_configuration(card)["eth"]
        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]].value
        except KeyError:
            return None
        path = "" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else eth.Api.PATH
        try:
            return card.get_public_key(derivation, path=path, compressed=False)
        except Exception:
            return None

    @staticmethod
    def _fetch_xrp_pubkey(card):
        try:
            return card.get_public_key(
                cryptnox_sdk_py.Derivation.DERIVE,
                path=xrp_wallet.PATH
            )
        except Exception:
            return None

    @staticmethod
    def _get_btc_info(card, pubkey) -> dict:
        if pubkey is None:
            return {"name": "BTC", "address": "Bad derivation type", "network": ""}
        config = get_configuration(card)["btc"]
        network = config.get("network", "testnet").lower()
        endpoint = BlkHubApi(network)
        wallet = BTCwallet(pubkey, network, endpoint, card)

        tabulate_data = {
            "name": "BTC",
            "address": wallet.address,
            "network": f"{network}"
                       f"\n   -{wallet.api.url.replace('https://', '')}"
        }

        try:
            tabulate_data["balance"] = f"{wallet.get_balance() / 10.0 ** 8} BTC"
        except Exception as error:
            print(f"There's an issue in retrieving BTC data: {error}")
            tabulate_data["balance"] = "Network issue"

        return tabulate_data

    @staticmethod
    def _get_eth_info(card, public_key) -> dict:
        if public_key is None:
            return {"name": "ETH", "address": "Bad derivation type", "network": ""}
        config = get_configuration(card)["eth"]
        network = enums.EthNetwork[config.get("network", "infura").upper()]
        try:
            api = eth.Api(config["endpoint"], network, config["api_key"])
        except ValueError as error:
            print(error)
            return {}

        address = eth.checksum_address(public_key)

        tabulate_data = {
            "name": "ETH",
            "address": address,
            "network": f"{network.name.lower()}\n   -{api.endpoint.domain}"
        }

        try:
            tabulate_data["balance"] = f"{web3.Web3.from_wei(api.get_balance(address), 'ether')} ETH"
        except Exception as error:
            print(f"There's an issue in retrieving ETH data: {error}")
            tabulate_data["balance"] = "Network issue"

        return tabulate_data

    @staticmethod
    def _get_xrp_info(pubkey) -> dict:
        tabulate_data = {"name": "XRP", "network": "mainnet", "balance": "--"}
        if pubkey is None:
            tabulate_data["address"] = "Error"
            return tabulate_data
        try:
            tabulate_data["address"] = xrp_wallet.address(pubkey)
        except Exception as error:
            print(f"There's an issue in retrieving XRP address: {error}")
            tabulate_data["address"] = "Error"
            return tabulate_data

        try:
            balance = xrp_wallet.get_balance(tabulate_data["address"])
            tabulate_data["balance"] = f"{balance} XRP"
        except Exception as error:
            print(f"There's an issue in retrieving XRP balance: {error}")
            tabulate_data["balance"] = "Network issue"

        return tabulate_data

    @staticmethod
    def _get_bnb_info(public_key) -> dict:
        # BNB on Binance Smart Chain (BSC) is EVM-compatible: same secp256k1
        # curve, same derivation path, and same address format as Ethereum.
        if public_key is None:
            return {"name": "BNB", "address": "Bad derivation type", "network": "BSC mainnet"}

        tabulate_data = {"name": "BNB", "network": "BSC mainnet", "balance": "--"}
        try:
            tabulate_data["address"] = eth.checksum_address(public_key)
        except Exception as error:
            print(f"There's an issue in retrieving BNB address: {error}")
            tabulate_data["address"] = "Error"
            return tabulate_data

        try:
            w3 = web3.Web3(web3.Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))
            balance_wei = w3.eth.get_balance(tabulate_data["address"])
            tabulate_data["balance"] = f"{web3.Web3.from_wei(balance_wei, 'ether')} BNB"
        except Exception as error:
            print(f"There's an issue in retrieving BNB balance: {error}")
            tabulate_data["balance"] = "Network issue"

        return tabulate_data

    @staticmethod
    def _print_info_table(info: List[Dict]) -> None:
        print("\n")

        to_print = {
            "name": "No name",
            "network": "No network",
            "address": "No address",
            "balance": "--",
        }

        tabulate_header = (
            "SERVICE",
            "NETWORK",
            "ACCOUNT",
            "BALANCE",
        )

        tabulate_table = []

        for element in info:
            row = [element.get(key, val) for key, val in to_print.items()]
            tabulate_table.append(row)

        print(tabulate(tabulate_table, headers=tabulate_header,
                       colalign=("left", "left", "left", "right")))
