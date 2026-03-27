# -*- coding: utf-8 -*-
"""
Module containing command for sending funds
"""
from typing import List

import cryptnox_sdk_py

from .command import Command
from .helper.config import create_config_method
from .helper.helper_methods import sign
from .helper.security import check_pin_code

try:
    import enums
    from config import get_configuration
    from wallet.btc import BTCwallet, BlkHubApi
except ImportError:
    from .. import enums
    from ..config import get_configuration
    from ..wallet.btc import BTCwallet, BlkHubApi, get_btc_api


class Btc(Command):
    """
    Command for sending payment on Bitcoin and Ethereum networks
    """
    _name = enums.Command.BTC.value

    def _execute(self, card) -> int:
        if card.type != ord("B"):
            print("Method not supported with this card type.")
            return -2

        self._check(card)

        if self.data.action == "send":
            self._send(card)
        if self.data.action == "config":
            return create_config_method(card, self.data.key, self.data.value, "btc")

        return 0

    def _send(self, card: cryptnox_sdk_py.Card) -> None:
        config = get_configuration(card)["btc"]
        network = self.data.network or config.get("network", "testnet")

        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]]
        except KeyError:
            print("Derivation is invalid")
            return

        endpoint = get_btc_api(network, config.get("endpoint", ""), config.get("api_key", ""))

        path = b"" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else BTCwallet.PATH
        pubkey = card.get_public_key(derivation, path=path)

        wallet = BTCwallet(pubkey, network, endpoint, card)
        print("Sending BTC")
        amount = int(self.data.amount * 10 ** 8)
        card.derive(path=BTCwallet.PATH)

        if self.data.fees:
            fees = self.data.fees
        else:
            fees = endpoint.get_fee_estimates()
            print(f"\nUsing fee (override with -f): {fees} Satoshi\n")

        try:
            wallet.prepare(self.data.address, amount, fees)

            signatures = Btc._sign(card, derivation, wallet.data_hash)
            message = wallet.send(self.data.address, amount, signatures)
        except Exception as error:
            print(error)
            return

        if message.startswith("\nDONE"):
            print(f"\nTransaction id: {message[13:]}\nBalance might take 30 s to be refreshed")

    @staticmethod
    def _sign(card: cryptnox_sdk_py.Card, derivation: cryptnox_sdk_py.Derivation,
              data_hashes: List[bytes]) -> List[bytes]:
        signatures = []
        if card.auth_type == cryptnox_sdk_py.AuthType.PIN and len(data_hashes) > 1:
            pin_code = check_pin_code(card)
        else:
            pin_code = ""

        for index, data_hash in enumerate(data_hashes):
            print("\nSigning INPUT #", index + 1)
            signatures.append(sign(card, data_hash, derivation, path=BTCwallet.PATH, pin_code=pin_code))

        return signatures
