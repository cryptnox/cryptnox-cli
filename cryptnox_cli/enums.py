# -*- coding: utf-8 -*-
"""
Module for defining enumerations used throughout the CryptnoxPro application.
"""

from enum import Enum


class EthNetwork(Enum):
    """
    Class defining possible Ethereum networks
    """
    MAINNET = 1
    KOVAN = 42
    GOERLI = 5
    RINKEBY = 4
    SEPOLIA = 11155111


class SolanaNetwork(Enum):
    """
    Class defining possible Solana networks
    """
    MAINNET = 1
    DEVNET = 2
    TESTNET = 3


class Command(Enum):
    BTC = "btc"
    CARD_CONFIGURATION = "card_conf"
    CHANGE_PIN = "change_pin"
    CHANGE_PUK = "change_puk"
    CONFIG = "config"
    ETH = "eth"
    HISTORY = "history"
    INFO = "info"
    INITIALIZE = "init"
    CARD = "list"
    SERVER = "server"
    RESET = "reset"
    SEED = "seed"
    SOLANA = "solana"
    UNLOCK_PIN = "unlock_pin"
    USER_KEY = "user_key"
    TRANSFER = "transfer"
    CERTIFICATE = "cert"
