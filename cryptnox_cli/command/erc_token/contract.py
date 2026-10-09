# -*- coding: utf-8 -*-
"""
Module for handling smart contract interactions for ERC tokens including
token transfers, balance checking, gas estimation, and transaction building
for ERC20, ERC721, and ERC1155 token standards.
"""

import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Tuple, Union

import cryptnox_sdk_py
import requests
from tabulate import tabulate

from ..helper.helper_methods import sign

try:
    from lib import cryptos
    from wallet import eth as wallet
except ImportError:
    from ...lib import cryptos
    from ...wallet import eth as wallet

LIMIT = {
    "transfer": 21000,
    "contract": 180000
}


def abi(value: int):
    try:
        folder = Path(__file__).parent.parent.parent.joinpath("contract_abi")
        return json.loads(folder.joinpath(f"erc{value}.json").absolute().read_text())
    except (FileNotFoundError, PermissionError, json.decoder.JSONDecodeError):
        raise ValueError("ERC not recognized by the application.")


def gas(gas_price: int, set_price: int, set_limit: int,
        default_limit: int = LIMIT["transfer"]) -> Tuple[int, int]:
    import web3

    if set_price:
        price = set_price
    else:
        gwei_price = math.ceil(web3.Web3.from_wei(gas_price, "gwei"))
        price = int(web3.Web3.to_wei(gwei_price, "gwei"))
        print(f"\nUsing gas price (override with -p): {gwei_price} Gwei")

    if set_limit:
        limit = set_limit
    else:
        if set_price:
            print()
        limit = default_limit
        print(f"Using gas limit (override with -l): {limit}")

    if not set_price or not set_limit:
        print()

    return price, limit


def transfer(card, endpoint, network, api_key, contract_address: str, to: str, amount: float,
             price: int, limit: int,
             derivation: cryptnox_sdk_py.Derivation = cryptnox_sdk_py.Derivation.CURRENT_KEY) -> int:
    import web3

    try:
        endpoint = wallet.Api(endpoint, network, api_key)
    except ValueError as error:
        print(error)
        return -1

    try:
        contract = endpoint.contract(address=contract_address, abi=abi(20))
    except ValueError as error:
        print(error)
        return -1
    except web3.exceptions.InvalidAddress as error:
        print(error.args[0])
        return -1

    path = wallet.Api.PATH if derivation != cryptnox_sdk_py.Derivation.CURRENT_KEY else ""
    public_key = card.get_public_key(derivation, path=path, compressed=False)
    address = wallet.checksum_address(public_key)

    try:
        symbol = contract.get_function_by_name("symbol")().call()
    except (TypeError, web3.exceptions.BadFunctionCallOutput) as error:
        print(error)
        return 2
    except web3.exceptions.ContractLogicError as error:
        print(f"Error occurred with execution: {error}")
        return -4

    try:
        token_balance = contract.get_function_by_name("balanceOf")(address).call()
    except (TypeError, web3.exceptions.BadFunctionCallOutput) as error:
        print(error)
        return 2
    except web3.exceptions.ContractLogicError as error:
        print(f"Error occurred with execution: {error}")
        return -4

    if token_balance - amount < 0:
        print(f"Not enough {symbol} for transfer")
        return -2

    function = contract.get_function_by_name("transfer")

    price, limit = gas(endpoint.gas_price, price, limit, LIMIT["contract"])

    nonce = endpoint.get_transaction_count(address)

    balance = endpoint.get_balance(address)
    if balance - price * limit < 0:
        print("Not enough fund for the transaction")
        return -2

    try:
        set_data = function(to, int(amount)).build_transaction({
            "nonce": nonce,
            "gasPrice": price,
            "gas": limit
        })
    except web3.exceptions.ContractLogicError as error:
        print(f"Error occurred with execution: {error}")
        return -4

    print("\nSigning with the Cryptnox")
    digest = endpoint.transaction_hash(set_data)
    signature = sign(card, digest, derivation, path=path)

    if not signature:
        print("Error in getting signature")
        return -1

    if not _confirm_token_sending(contract.address, address, to, token_balance, symbol, amount,
                                  balance, price, limit):
        print("Canceled by user")
        return -1

    try:
        transaction = endpoint.push(set_data, signature, public_key)
    except requests.exceptions.RequestException as error:
        print(f"Error occurred in communication with the server: {error}")
        return 3
    except ValueError as error:
        print(error.args[0]["message"])
        return 4

    print(f"Request sent to network. Transaction id: {transaction.hex()}. "
          f"It can take some time until you can see the change.")

    return 0


def _confirm_token_sending(contract: str, address: str, to: str,
                           token_balance: float, symbol: str, value: Union[Decimal, int],
                           balance: int, price: int, limit: float):
    import web3

    gas_price = web3.Web3.from_wei(price, "ether")
    total_gas = Decimal(gas_price * limit)
    balance = web3.Web3.from_wei(balance, "ether")
    tabulate_table = [
        ["", "", "", ],
        ["BALANCE:", token_balance, symbol, "CONTRACT: ", contract],
        ["TRANSACTION:", value, symbol, "ACCOUNT:", address],
        ["BALANCE: ", balance, "ETH", "TO:", to],
        ["GAS:", total_gas, "ETH"]
    ]

    floating_points = max(cryptos.wallet_utils.number_of_significant_digits((total_gas + value)), 8)

    print("\n\n--- Transaction Ready --- \n")
    print(tabulate(tabulate_table, tablefmt='plain',
                   floatfmt=f".{floating_points}f"), "\n")
    conf = input("Confirm ? [y/N] > ")

    return conf.lower() == "y"
