# -*- coding: utf-8 -*-
"""
Solana (Ed25519) address derivation, balance lookup and native-SOL transaction
building.

Unlike Bitcoin/Ethereum/XRP, a Solana address is **not** a hash of the public
key: it is simply the base58 encoding of the raw 32-byte Ed25519 public key.

Transaction building, message serialization and final transaction assembly are
delegated to ``solders`` (the Rust Solana SDK Python bindings). The card signs
the *raw transaction message bytes* (Ed25519 is pure, the card hashes
internally), and the resulting 64-byte signature is grafted onto the message to
produce the broadcastable transaction.
"""
import base64

import base58
import requests
from cryptnox_sdk_py import Derivation
from solders.hash import Hash
from solders.message import Message
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from . import validators

try:
    import enums
except ImportError:
    from .. import enums

# Solana derivation path used by Phantom and most wallets (all-hardened SLIP-0010)
PATH = "m/44'/501'/0'/0'"

# 1 SOL = 1 000 000 000 lamports
LAMPORTS_PER_SOL = 1_000_000_000

# Flat per-signature base fee. A native transfer carries a single signature, so
# this is the worst-case network fee for the balance check.
BASE_FEE_LAMPORTS = 5_000

MAINNET = "https://api.mainnet-beta.solana.com"
DEVNET = "https://api.devnet.solana.com"
TESTNET = "https://api.testnet.solana.com"

_NETWORK_RPC = {
    "mainnet": MAINNET,
    "devnet": DEVNET,
    "testnet": TESTNET,
}


def rpc_url(network: str, endpoint: str = "") -> str:
    """
    Resolve the JSON-RPC URL to use.

    A non-empty ``endpoint`` override always wins; otherwise the URL is derived
    from the network name, defaulting to mainnet for unknown values.

    :param str network: Network name (mainnet/devnet/testnet)
    :param str endpoint: Optional explicit RPC URL override
    :return: RPC URL to use
    :rtype: str
    """
    if endpoint:
        return endpoint
    return _NETWORK_RPC.get((network or "mainnet").lower(), MAINNET)


def address(public_key_hex: str) -> str:
    """
    Derive a Solana address from a raw Ed25519 public key.

    A Solana address is the base58 of the raw 32-byte key - there is no hashing.

    :param str public_key_hex: Raw 32-byte Ed25519 public key as hex (64 chars)
    :return: Base58 Solana address
    :rtype: str
    """
    return base58.b58encode(bytes.fromhex(public_key_hex)).decode()


def build_transfer_message(from_public_key_hex: str, to_address: str, lamports: int,
                           recent_blockhash: str) -> Message:
    """
    Build a System-Program transfer message with the sender as fee-payer.

    :param str from_public_key_hex: Sender raw Ed25519 public key as hex
    :param str to_address: Recipient base58 address
    :param int lamports: Amount to transfer in lamports
    :param str recent_blockhash: Recent blockhash as a base58 string
    :return: The (unsigned) message; ``bytes(message)`` are what the card signs
    :rtype: solders.message.Message
    """
    from_pubkey = Pubkey.from_bytes(bytes.fromhex(from_public_key_hex))
    to_pubkey = Pubkey.from_string(to_address)
    instruction = transfer(TransferParams(from_pubkey=from_pubkey, to_pubkey=to_pubkey,
                                          lamports=lamports))
    blockhash = Hash.from_string(recent_blockhash)
    return Message.new_with_blockhash([instruction], from_pubkey, blockhash)


def assemble_transaction(message: Message, signature: bytes) -> Transaction:
    """
    Graft a card-produced 64-byte signature onto a message to build the final
    broadcastable transaction.

    :param solders.message.Message message: Message that was signed
    :param bytes signature: Raw 64-byte Ed25519 signature from the card
    :return: Fully signed transaction
    :rtype: solders.transaction.Transaction
    """
    return Transaction.populate(message, [Signature.from_bytes(signature)])


class SolanaApi:
    """
    Thin JSON-RPC client for the Solana network (balance, blockhash, broadcast).
    """

    def __init__(self, network: str = "mainnet", endpoint: str = ""):
        self.url = rpc_url(network, endpoint)

    def _rpc(self, method: str, params: list):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = requests.post(self.url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise ValueError(data["error"].get("message", "Solana RPC error"))
        return data["result"]

    def get_balance(self, sol_address: str) -> int:
        """
        Return the balance of *sol_address* in lamports.

        Kept as an integer end-to-end; converting to SOL (float) and back would
        risk off-by-one errors in the funds check.
        """
        result = self._rpc("getBalance", [sol_address])
        return result["value"]

    def get_latest_blockhash(self) -> str:
        """
        Return a recent blockhash as a base58 string.

        Uses ``confirmed`` (not ``finalized``): a finalized blockhash lags ~32
        slots, so it has already burned part of its validity window and can
        expire during a slow confirmation.
        """
        result = self._rpc("getLatestBlockhash", [{"commitment": "confirmed"}])
        return result["value"]["blockhash"]

    def send_transaction(self, transaction: Transaction) -> str:
        """
        Broadcast a signed transaction (base64-encoded) and return its signature.
        """
        encoded = base64.b64encode(bytes(transaction)).decode()
        return self._rpc("sendTransaction", [encoded, {"encoding": "base64"}])


class SolanaValidator:
    """
    Class defining Solana configuration validators
    """
    derivation = validators.EnumValidator(Derivation)
    network = validators.EnumValidator(enums.SolanaNetwork)
    endpoint = validators.AnyValidator()

    def __init__(self, derivation: str = "DERIVE", network: str = "mainnet",
                 endpoint: str = ""):
        self.derivation = derivation
        self.network = network
        self.endpoint = endpoint

    def validate(self):
        # All per-field validation happens on assignment via the descriptors.
        return None
