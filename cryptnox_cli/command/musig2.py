# -*- coding: utf-8 -*-
"""
Module containing the ``musig2`` command for MuSig2 (BIP-327) multi-signature
operations with Cryptnox Basic G2 cards.

The Basic G2 card exposes three extra instructions used here over the encrypted
secure channel:

* ``C2 00 01``     -- read the card's MuSig2 public key
* ``C7 00 00``     -- generate this card's pair of signing nonces (R1 || R2)
* ``C8 01 00``     -- load a cosigner public key (repeated for every signer)
* ``C8 02 00``     -- produce this card's partial signature

The byte layout of these calls matches the reference ``cryptnox-cli-musig2``
scripts, which were validated against the card firmware.  All public-key/nonce
aggregation and the Schnorr/Taproot math are done on the host in
:mod:`cryptnox_cli.command.musig2_crypto`.

Because MuSig2 needs every signer's card and this build targets a single reader,
the command walks the user through inserting each card in turn (the same
"insert card N, press ENTER" flow as the reference scripts).
"""

import hashlib

import cryptnox_sdk_py
import requests

from .command import Command
from .helper.cards import ExitException
from .helper.security import check
from . import musig2_crypto as mc

try:
    import enums
except ImportError:
    from .. import enums


# MuSig2 applet instructions (see module docstring)
_INS_GET_PUBKEY = [0x00, 0xC2, 0x00, 0x01]
_INS_NONCE_GEN = [0x00, 0xC7, 0x00, 0x00]
_INS_SIGN = 0xC8
_P1_LOAD_COSIGNER = 0x01
_P1_PARTIAL_SIGN = 0x02

# Length of the partial-signature input: aggR1(65) + aggR2(65) + aggPk(33) + msg(32)
_SIGN_DATA_LENGTH = 195

_NETWORKS = {
    "testnet": {"hrp": "tb", "api": "https://mempool.space/testnet/api"},
    "mainnet": {"hrp": "bc", "api": "https://mempool.space/api"},
}

# Standard dust threshold (sats) below which an output is not economically spendable.
_DUST_LIMIT = 546


class Musig2(Command):
    """
    Command for MuSig2 (BIP-327) multi-signature operations on Basic G2 cards.
    """
    _name = enums.Command.MUSIG2.value

    # ------------------------------------------------------------------
    # Entry point -- overrides Command.execute() because this command drives
    # several cards through a single reader instead of one pre-selected card.
    # ------------------------------------------------------------------
    def execute(self, serial_number: int = None) -> int:
        self._debug = bool(getattr(self.data, "verbose", False))
        action = getattr(self.data, "action", None)

        try:
            if action == "address":
                return self._address()
            if action == "sign":
                return self._sign()
            if action == "send":
                return self._send()
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return -1
        except cryptnox_sdk_py.exceptions.GenericException as error:
            print(f"\nThe card rejected a MuSig2 command (status 0x{error.status.hex().upper()}).")
            print("This usually means the card is not a Basic G2 card with MuSig2 support.")
            return -2
        except cryptnox_sdk_py.exceptions.CryptnoxException as error:
            print(error)
            return -1
        except cryptnox_sdk_py.exceptions.CardClosedException:
            print("\nLost contact with the card. Please keep the card on the reader and retry.")
            return -1
        except (ExitException, EOFError):
            print("\nCancelled by user.")
            return -1

        print("Unknown MuSig2 action. Use 'address', 'sign' or 'send'.")
        return -1

    # _execute is required by the abstract base class but is never reached
    # because execute() is overridden for the multi-card flow.
    def _execute(self, card) -> int:  # pragma: no cover - not used
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Card connection / reader helpers (single reader, card swaps)
    # ------------------------------------------------------------------
    def _reader_index(self) -> int:
        return int(getattr(self.data, "reader", 0) or 0)

    def _connect(self, label: str):
        """Open a fresh connection, recognise the card and verify it for signing."""
        connection = cryptnox_sdk_py.Connection(self._reader_index(), self._debug)
        card = cryptnox_sdk_py.factory.get_card(connection, self._debug)

        if card.type != ord("B"):
            connection.disconnect()
            raise cryptnox_sdk_py.exceptions.CryptnoxException(
                "MuSig2 is only supported on Cryptnox Basic G2 cards.")

        # Ensure the card is initialised, has a seed and is authenticated (PIN).
        check(card)

        print(f"  [{label}] connected, serial: {card.serial_number}")
        return connection, card

    @staticmethod
    def _wait_swap(message: str) -> None:
        input(f"\n>>> {message}, then press ENTER...")

    # ------------------------------------------------------------------
    # MuSig2 card instructions
    # ------------------------------------------------------------------
    @staticmethod
    def _get_pubkey(connection) -> bytes:
        return mc.compressed_pubkey(connection.send_encrypted(_INS_GET_PUBKEY, b""))

    @staticmethod
    def _nonce_gen(connection):
        response = connection.send_encrypted(_INS_NONCE_GEN, b"")
        if len(response) < 66:
            raise cryptnox_sdk_py.exceptions.DataException(
                "Bad nonce response from card (expected 66 bytes).")
        return response[:33], response[33:66]

    @staticmethod
    def _load_cosigner(connection, pk: bytes) -> None:
        connection.send_encrypted([0x00, _INS_SIGN, _P1_LOAD_COSIGNER, 0x00], pk)

    @staticmethod
    def _partial_sign(connection, data: bytes) -> bytes:
        return connection.send_encrypted([0x00, _INS_SIGN, _P1_PARTIAL_SIGN, 0x00], data)

    def _sign_with_card(self, connection, sorted_pks, sign_data: bytes) -> bytes:
        for pk in sorted_pks:
            self._load_cosigner(connection, pk)
        return self._partial_sign(connection, sign_data)

    # ------------------------------------------------------------------
    # Phase 1 -- collect every card's public key and nonces
    # ------------------------------------------------------------------
    def _collect_pubkeys_and_nonces(self, num_signers: int):
        """
        Walk through every card once, reading its public key and nonces.

        :return: tuple (pubkeys, nonces_r1, nonces_r2, last_connection). The last
                 card's connection is left open so it can sign first in phase 2.
        """
        pubkeys, nonces_r1, nonces_r2 = [], [], []
        previous_connection = None

        for index in range(1, num_signers + 1):
            if previous_connection is not None:
                previous_connection.disconnect()
            self._wait_swap(f"Insert CARD {index}")

            print(f"\n--- Phase 1.{index}: public key + nonce generation ---")
            connection, _ = self._connect(f"Card{index}")
            pubkey = self._get_pubkey(connection)
            nonce_r1, nonce_r2 = self._nonce_gen(connection)
            print(f"  pk{index}: {pubkey.hex()}")
            pubkeys.append(pubkey)
            nonces_r1.append(nonce_r1)
            nonces_r2.append(nonce_r2)
            previous_connection = connection

        return pubkeys, nonces_r1, nonces_r2, previous_connection

    # ------------------------------------------------------------------
    # Phase 2 -- collect a partial signature from every card
    # ------------------------------------------------------------------
    def _collect_partial_signatures(self, num_signers: int, sorted_pks, sign_data: bytes,
                                    last_connection) -> list:
        """Gather one partial signature per card, starting with the inserted last card."""
        partial_sigs = [None] * num_signers

        print(f"\n--- Phase 2.{num_signers}: partial signature (card already inserted) ---")
        partial_sigs[num_signers - 1] = self._sign_with_card(last_connection, sorted_pks, sign_data)
        print(f"  s{num_signers}: {partial_sigs[num_signers - 1].hex()}")
        previous_connection = last_connection

        for index in range(1, num_signers):
            previous_connection.disconnect()
            self._wait_swap(f"Insert CARD {index}")
            print(f"\n--- Phase 2.{index}: partial signature ---")
            connection, _ = self._connect(f"Card{index}")
            partial_sigs[index - 1] = self._sign_with_card(connection, sorted_pks, sign_data)
            print(f"  s{index}: {partial_sigs[index - 1].hex()}")
            previous_connection = connection

        previous_connection.disconnect()
        return partial_sigs

    @staticmethod
    def _sum_partials(partial_sigs) -> int:
        return sum(int.from_bytes(s, "big") for s in partial_sigs) % mc.N

    # ------------------------------------------------------------------
    # Argument helpers
    # ------------------------------------------------------------------
    def _num_signers(self) -> int:
        num = int(self.data.signers)
        if num < 2:
            raise cryptnox_sdk_py.exceptions.DataValidationException(
                "MuSig2 needs at least 2 signers.")
        return num

    def _message_hash(self) -> bytes:
        text = getattr(self.data, "text", None)
        message = getattr(self.data, "message", None)
        if text is not None:
            return hashlib.sha256(text.encode()).digest()
        if message:
            digest = bytes.fromhex(message)
            if len(digest) != 32:
                raise cryptnox_sdk_py.exceptions.DataValidationException(
                    "--message must be a 32-byte (64 hex character) value.")
            return digest
        raise cryptnox_sdk_py.exceptions.DataValidationException(
            "Provide a message with --message <hex32> or --text <string>.")

    def _network(self):
        name = getattr(self.data, "network", None) or "testnet"
        return name, _NETWORKS[name]

    # ------------------------------------------------------------------
    # Sub-commands
    # ------------------------------------------------------------------
    def _aggregate(self, num_signers: int):
        """Phase 1 + host-side aggregation shared by all sub-commands."""
        pubkeys, nonces_r1, nonces_r2, last_connection = \
            self._collect_pubkeys_and_nonces(num_signers)

        sorted_pks = sorted(pubkeys)
        aggpk_c, aggpk_x = mc.aggregate_pubkey(sorted_pks)
        agg_r1, agg_r2 = mc.aggregate_nonces(nonces_r1, nonces_r2)

        print(f"\n  Aggregate public key: {aggpk_c.hex()}")
        return sorted_pks, aggpk_c, aggpk_x, agg_r1, agg_r2, last_connection

    def _address(self) -> int:
        num_signers = self._num_signers()
        _, network = self._network()

        print("=" * 60)
        print(f"  MuSig2 Taproot address -- {num_signers} signers")
        print("=" * 60)

        sorted_pks, _, aggpk_x, _, _, last_connection = self._aggregate(num_signers)
        last_connection.disconnect()

        _, output_x, _, _ = mc.taproot_output_key(aggpk_x)
        address = mc.encode_taproot_address(output_x, network["hrp"])

        print(f"\n  Internal key (x-only): {aggpk_x.hex()}")
        print(f"  Output key   (x-only): {output_x.hex()}")
        print(f"\n  *** Taproot address: {address} ***")
        return 0

    def _sign(self) -> int:
        num_signers = self._num_signers()
        message = self._message_hash()

        print("=" * 60)
        print(f"  MuSig2 sign -- {num_signers} signers")
        print("=" * 60)
        print(f"  Message hash: {message.hex()}")

        sorted_pks, aggpk_c, aggpk_x, agg_r1, agg_r2, last_connection = \
            self._aggregate(num_signers)

        sign_data = mc.point_to_uncompressed(agg_r1) + mc.point_to_uncompressed(agg_r2) \
            + aggpk_c + message
        assert len(sign_data) == _SIGN_DATA_LENGTH

        partial_sigs = self._collect_partial_signatures(
            num_signers, sorted_pks, sign_data, last_connection)

        s_agg = self._sum_partials(partial_sigs)
        nonce_x = mc.effective_nonce_x(agg_r1, agg_r2, aggpk_x, message)
        signature = nonce_x + s_agg.to_bytes(32, "big")

        print("\n--- Result ---")
        print(f"  Signature: {signature.hex()}")

        if mc.schnorr_verify(aggpk_x, message, signature):
            print("  BIP-340 Schnorr verification: PASS")
            return 0

        print("  BIP-340 Schnorr verification: FAIL")
        return -1

    def _send(self) -> int:
        num_signers = self._num_signers()
        network_name, network = self._network()
        destination = self.data.address

        print("=" * 60)
        print(f"  MuSig2 Taproot transaction -- {num_signers} signers ({network_name})")
        print("=" * 60)

        sorted_pks, aggpk_c, aggpk_x, agg_r1, agg_r2, last_connection = \
            self._aggregate(num_signers)

        output_c, output_x, tweak, q_even = mc.taproot_output_key(aggpk_x)
        our_spk = b"\x51\x20" + output_x
        address = mc.encode_taproot_address(output_x, network["hrp"])
        print(f"\n  Source Taproot address: {address}")

        # ---- gather UTXOs (host / network) ----
        try:
            utxos = self._get_utxos(network["api"], address)
        except requests.exceptions.RequestException as error:
            last_connection.disconnect()
            print(f"  Could not reach the blockchain API: {error}")
            return -1

        if not utxos:
            last_connection.disconnect()
            print("\n  No UTXOs found. Fund the address above and try again.")
            return -1

        try:
            inputs, outputs, amounts, fee = self._build_outputs(
                utxos, destination, our_spk, network["api"])
        except ValueError as error:
            last_connection.disconnect()
            print(f"  {error}")
            return -1

        sighash = mc.compute_sighash_taproot(2, 0, inputs, outputs, 0, amounts, [our_spk])
        print(f"  Sighash: {sighash.hex()}")
        print(f"  Fee:     {fee} sats")

        if not self._confirm(network_name):
            last_connection.disconnect()
            print("  Aborted.")
            return -1

        # ---- card-side partial signatures over the Taproot sighash ----
        p_even = mc.has_even_y(aggpk_c)
        card_aggpk = output_c if p_even else mc.negate_compressed(output_c)
        sign_data = mc.point_to_uncompressed(agg_r1) + mc.point_to_uncompressed(agg_r2) \
            + card_aggpk + sighash
        assert len(sign_data) == _SIGN_DATA_LENGTH

        partial_sigs = self._collect_partial_signatures(
            num_signers, sorted_pks, sign_data, last_connection)

        # ---- aggregate + apply the Taproot tweak ----
        s_agg = self._sum_partials(partial_sigs)
        nonce_x = mc.effective_nonce_x(agg_r1, agg_r2, mc.xonly(card_aggpk), sighash)
        challenge = mc.tagged_hash("BIP0340/challenge", nonce_x + output_x + sighash)
        e = int.from_bytes(challenge, "big") % mc.N
        if q_even:
            s_final = (s_agg + e * tweak) % mc.N
        else:
            s_final = (s_agg - e * tweak) % mc.N
        signature = nonce_x + s_final.to_bytes(32, "big")

        if not mc.schnorr_verify(output_x, sighash, signature):
            print("\n  ERROR: aggregate signature failed local verification, not broadcasting.")
            return -1
        print("\n  BIP-340 Schnorr verification: PASS")

        signed_tx = mc.build_signed_tx(2, 0, inputs, outputs, signature)
        tx_hex = signed_tx.hex()

        try:
            txid = self._broadcast(network["api"], tx_hex)
        except requests.exceptions.RequestException as error:
            print(f"  Broadcast error: {error}")
            print(f"  Raw transaction: {tx_hex}")
            return -1

        print(f"\n  SUCCESS! Transaction id: {txid}")
        return 0

    # ------------------------------------------------------------------
    # Transaction construction (single input, sweep or amount + change)
    # ------------------------------------------------------------------
    def _build_outputs(self, utxos, destination, our_spk, api):
        fee_rate = self._get_fee_rate(api)
        dest_spk = mc.decode_address_to_scriptpubkey(destination)

        # Spend the first UTXO only (keeps the example simple and deterministic).
        first = utxos[0]
        if len(utxos) > 1:
            print(f"  NOTE: {len(utxos)} UTXOs found, using only the first one.")
        inputs = [(first["txid"], first["vout"], 0xfffffffd)]
        amounts = [first["value"]]
        input_total = first["value"]

        amount = getattr(self.data, "amount", None)
        if amount is not None:
            num_outputs = 2
            est_vsize = 10.5 + 58 + 43 * num_outputs
            fee = int(est_vsize * fee_rate) + 10
            send_amount = int(amount)
            if send_amount <= _DUST_LIMIT:
                raise ValueError(f"Amount too small (dust limit is {_DUST_LIMIT} sats).")
            change = input_total - send_amount - fee
            if change < 0:
                raise ValueError(
                    f"Not enough funds: need {send_amount + fee}, have {input_total}.")
            outputs = [(send_amount, dest_spk)]
            if change > _DUST_LIMIT:
                outputs.append((change, our_spk))
                print(f"  Send:   {send_amount} sats")
                print(f"  Change: {change} sats")
            else:
                fee += change
                print(f"  Send:   {send_amount} sats (dust change {change} added to fee)")
        else:
            num_outputs = 1
            est_vsize = 10.5 + 58 + 43 * num_outputs
            fee = int(est_vsize * fee_rate) + 10
            send_amount = input_total - fee
            if send_amount <= _DUST_LIMIT:
                raise ValueError(
                    f"Not enough funds: balance {input_total}, fee {fee}.")
            outputs = [(send_amount, dest_spk)]
            print(f"  Sweep:  {send_amount} sats (entire balance minus fee)")

        return inputs, outputs, amounts, fee

    @staticmethod
    def _confirm(network_name: str) -> bool:
        prompt = "\n  Broadcast this transaction"
        if network_name == "mainnet":
            prompt += " on MAINNET (real funds)"
        answer = input(prompt + "? [y/N]: ").strip().lower()
        return answer in ("y", "yes")

    # ------------------------------------------------------------------
    # Blockchain API (mempool.space)
    # ------------------------------------------------------------------
    @staticmethod
    def _get_utxos(api: str, address: str):
        response = requests.get(f"{api}/address/{address}/utxo", timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _get_fee_rate(api: str) -> int:
        try:
            response = requests.get(f"{api}/v1/fees/recommended", timeout=30)
            response.raise_for_status()
            return response.json().get("halfHourFee", 2)
        except requests.exceptions.RequestException:
            return 2

    @staticmethod
    def _broadcast(api: str, tx_hex: str) -> str:
        response = requests.post(f"{api}/tx", data=tx_hex, timeout=30)
        if response.status_code == 200:
            return response.text
        raise requests.exceptions.HTTPError(
            f"broadcast failed ({response.status_code}): {response.text}")
