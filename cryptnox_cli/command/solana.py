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
        except requests.RequestException as error:
            # requests.HTTPError is a subclass, so this covers both.
            print(f"There was an issue in communication: {error}")
            return -1
        except ValueError as error:
            print(f"Solana network error: {error}")
            return -1

        return 0

    def _send(self, card) -> int:
        if not wallet.sdk_supports_ed25519():
            print("This version of cryptnox-sdk-py does not support Solana (Ed25519).\n"
                  "Update it with: pip install --upgrade cryptnox-sdk-py")
            return -1

        config = get_configuration(card)["solana"]

        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]]
        except KeyError:
            print("Derivation is invalid")
            return 1

        # An explicit --network must never be silently overridden by a configured
        # endpoint (which may point at a different network); ignore the override then.
        explicit_network = getattr(self.data, "network", None)
        network = explicit_network or config["network"]
        endpoint = "" if explicit_network else config["endpoint"]
        api = wallet.SolanaApi(network, endpoint)

        path = "" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else wallet.PATH
        public_key = card.get_public_key(derivation, key_type=cryptnox_sdk_py.KeyType.ED25519,
                                         path=path, compressed=False)
        from_address = wallet.address(public_key)

        lamports = int(self.data.amount * wallet.LAMPORTS_PER_SOL)
        if lamports <= 0:
            print("Amount is too small: it rounds to 0 lamports")
            return 1

        balance_lamports = api.get_balance_lamports(from_address)
        if balance_lamports < lamports + wallet.BASE_FEE_LAMPORTS:
            print("Not enough funds for the transaction")
            return -2

        if lamports < wallet.RENT_EXEMPT_LAMPORTS:
            print(f"\nWarning: {self.data.amount} SOL is below the rent-exempt minimum "
                  f"(~{wallet.RENT_EXEMPT_LAMPORTS / wallet.LAMPORTS_PER_SOL} SOL). "
                  "A transfer to a new account may be rejected by the network.")

        balance = balance_lamports / wallet.LAMPORTS_PER_SOL
        if not Solana._confirm(from_address, self.data.address, balance, self.data.amount,
                               api.url):
            print("Canceled by the user.")
            return -1

        # Confirm first, then fetch the blockhash and sign: the blockhash is only
        # valid for ~60-90 s, so fetching it before a blocking prompt risks expiry,
        # and signing before confirmation would consume the card counter on decline.
        blockhash = api.get_latest_blockhash()
        message = wallet.build_transfer_message(public_key, self.data.address, lamports, blockhash)
        message_bytes = bytes(message)

        print("\nSigning with the Cryptnox")
        try:
            signature = sign(card, message_bytes, derivation,
                             key_type=cryptnox_sdk_py.KeyType.ED25519, path=path)
        except ValueError as error:
            print(f"Error signing with the card: {error}")
            return -1

        # Belt-and-braces: reject a signature the card cannot verify against its
        # own derived key before we broadcast anything.
        if not wallet.verify_signature(public_key, message_bytes, signature):
            print("Card signature failed verification; aborting before broadcast.")
            return -1

        transaction = wallet.assemble_transaction(message, signature)
        tx_signature = api.send_transaction(transaction)

        print(f"\nTransaction id: {tx_signature}\n"
              f"Balance might take some time to be refreshed.")

        return 0

    @staticmethod
    def _confirm(from_address: str, to_address: str, balance: float, amount: Decimal,
                 rpc_url: str = "") -> bool:
        fee = Decimal(wallet.BASE_FEE_LAMPORTS) / wallet.LAMPORTS_PER_SOL

        def sol(value) -> str:
            # Fixed-point SOL amount; avoids Decimal/float exponent notation (e.g. 5E-6)
            return f"{Decimal(str(value)):f}"

        tabulate_table = [
            ["BALANCE:", sol(balance), "SOL", "ON", "ACCOUNT:", f"{from_address}"],
            ["TRANSACTION:", sol(amount), "SOL", "TO", "ACCOUNT:", f"{to_address}"],
            ["MAX FEE:", sol(fee)],
            ["MAX TOTAL:", sol(amount + fee)],
            ["NETWORK:", rpc_url],
        ]

        print("\n\n--- Transaction Ready --- \n")
        # disable_numparse: keep the pre-formatted fixed-point strings as-is;
        # otherwise tabulate re-parses them and renders e.g. 0.000005 as "5e-06".
        print(tabulate(tabulate_table, tablefmt='plain', disable_numparse=True), "\n")
        conf = input("Confirm ? [y/N] > ")

        return conf.lower() == "y"
