# -*- coding: utf-8 -*-
"""
Module containing command for transferring tokens
"""
import gzip
import json

from .command import Command
from .erc_token.contract import transfer

try:
    import enums
except ImportError:
    from .. import enums


class Transfer(Command):
    """
    Command for transferring tokens
    """
    _name = enums.Command.TRANSFER.value

    def _execute(self, card) -> int:
        if card.type != ord("N"):
            print("Method not supported with this card type.")
            return -2

        data = json.loads(gzip.decompress(card.user_data[0]).decode("UTF8"))

        if data.get("erc") != 20:
            print("Command only usable with ERC20 prepaid cards.")
            return -1

        try:
            network = enums.EthNetwork(data.get("chain_id"))
        except KeyError:
            print("Chain id not recognized")
            return -1

        return transfer(card, data.get("endpoint"), network, "", data.get("contract_address"),
                        self.data.address, self.data.amount, self.data.price, self.data.limit)
