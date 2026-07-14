# -*- coding: utf-8 -*-
"""
Module containing command for sending native SOL on the Solana network.

Solana uses the Ed25519 (EdDSA) curve, available on Cryptnox applet v2.0+. The
card derives the Ed25519 key, signs the raw transaction message bytes (Ed25519
is pure - the card hashes internally), and the resulting 64-byte signature is
assembled into a broadcastable transaction.
"""
from decimal import Decimal

import cryptnox_sdk_py
import requests
from tabulate import tabulate

from .command import Command
from .helper.config import create_config_method
from .helper.helper_methods import sign

try:
    import enums
    from config import get_configuration
    from wallet import solana as wallet
except ImportError:
    from .. import enums
    from ..config import get_configuration
    from ..wallet import solana as wallet


class Solana(Command):
    """
    Command for sending payment on the Solana network
    """
    _name = enums.Command.SOLANA.value

    def _execute(self, card) -> int:
        self._check(card)

        try:
            if self.data.solana_action == "send":
                return self._send(card)
            if self.data.solana_action == "config":
                return create_config_method(card, self.data.key, self.data.value, "solana")
        except requests.HTTPError as error:
            print(f"There was an issue in communication: {error}")
            return -1
        except requests.RequestException as error:
            print(f"There was an issue in communication: {error}")
            return -1
        except ValueError as error:
            print(f"Solana network error: {error}")
            return -1

        return 0

    def _send(self, card) -> int:
        config = get_configuration(card)["solana"]

        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]]
        except KeyError:
            print("Derivation is invalid")
            return 1

        # An explicit --network must win over a configured endpoint. Otherwise a
        # stored endpoint (typically mainnet) silently overrides --network devnet
        # and real funds go to the wrong cluster.
        explicit_network = getattr(self.data, "network", None)
        network = explicit_network or config["network"]
        endpoint = "" if explicit_network else config["endpoint"]
        api = wallet.SolanaApi(network, endpoint)

        path = "" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else wallet.PATH
        public_key = card.get_public_key(derivation, key_type=cryptnox_sdk_py.KeyType.ED25519,
                                         path=path, compressed=False)
        from_address = wallet.address(public_key)

        lamports = int(self.data.amount * wallet.LAMPORTS_PER_SOL)

        balance_lamports = api.get_balance(from_address)
        if balance_lamports < lamports + wallet.BASE_FEE_LAMPORTS:
            print("Not enough funds for the transaction")
            return -2

        balance_sol = Decimal(balance_lamports) / wallet.LAMPORTS_PER_SOL

        # Confirm BEFORE signing: declining must not leave a valid signed
        # transaction, and signing last keeps the blockhash as fresh as possible.
        if not Solana._confirm(from_address, self.data.address, balance_sol, self.data.amount):
            print("Canceled by the user.")
            return -1

        blockhash = api.get_latest_blockhash()
        message = wallet.build_transfer_message(public_key, self.data.address, lamports, blockhash)
        message_bytes = bytes(message)

        print("\nSigning with the Cryptnox")
        signature = sign(card, message_bytes, derivation,
                         key_type=cryptnox_sdk_py.KeyType.ED25519, path=path)
        if not signature:
            print("Error in getting signature")
            return -1

        transaction = wallet.assemble_transaction(message, signature)
        tx_signature = api.send_transaction(transaction)

        print(f"\nTransaction id: {tx_signature}\n"
              f"Balance might take some time to be refreshed.")

        return 0

    @staticmethod
    def _confirm(from_address: str, to_address: str, balance: Decimal, amount: Decimal) -> bool:
        fee = Decimal(wallet.BASE_FEE_LAMPORTS) / wallet.LAMPORTS_PER_SOL

        def sol(value) -> str:
            # Fixed-point SOL amount; avoids Decimal/float exponent notation (e.g. 5E-6)
            return f"{Decimal(str(value)):f}"

        tabulate_table = [
            ["BALANCE:", sol(balance), "SOL", "ON", "ACCOUNT:", f"{from_address}"],
            ["TRANSACTION:", sol(amount), "SOL", "TO", "ACCOUNT:", f"{to_address}"],
            ["MAX FEE:", sol(fee)],
            ["MAX TOTAL:", sol(amount + fee)],
        ]

        print("\n\n--- Transaction Ready --- \n")
        # disable_numparse: keep the pre-formatted fixed-point strings as-is;
        # otherwise tabulate re-parses them and renders e.g. 0.000005 as "5e-06".
        print(tabulate(tabulate_table, tablefmt='plain', disable_numparse=True), "\n")
        conf = input("Confirm ? [y/N] > ")

        return conf.lower() == "y"
