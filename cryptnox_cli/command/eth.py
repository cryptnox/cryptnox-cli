# -*- coding: utf-8 -*-
"""
Module containing command for sending funds
"""
import json
import re
import shutil
from decimal import Decimal
from typing import Dict, Any, List

import cryptnox_sdk_py
import requests
import web3
from argparse import Namespace
from tabulate import tabulate

from .command import Command
from .erc_token import contract
from .helper.config import create_config_method
from .helper.helper_methods import sign
from .helper.notification import MORE_THAN_X_RESULTS, MONTH_PERIOD_IN_BLOCKS

try:
    import enums
    from config import get_configuration, save_to_config
    from wallet import eth as wallet
    from lib import cryptos
except ImportError:
    from .. import enums
    from ..config import get_configuration, save_to_config
    from ..wallet import eth as wallet
    from ..lib import cryptos

_BLOCK_OFFSET = 500
_LARGE_SCREEN_SIZE = (4 - 1) * 3 + 4 + (64 + 2) + (42 + 2 + 6) + 8


class ApiKeyException(Exception):
    """
    API key is empty
    """


def _abi(config) -> List[Any]:
    try:
        return contract.abi(int(config))
    except ValueError:
        return json.loads(config)
    except TypeError:
        return config


def _large_screen():
    return shutil.get_terminal_size((80, 20)).columns > _LARGE_SCREEN_SIZE


def _get_processed_json_argument(data: str) -> str:
    result = data
    if isinstance(result, list):
        result = " ".join(result)
    result = result.strip("'")
    result = re.sub(r"(\w+):", r'"\1":', result)
    result = re.sub(r'(:\s?)(?!true|false|null)([a-zA-Z_]+[a-zA-Z0-9_]*)([,\s])',
                    r'\1"\2"\3', result)
    result = re.sub(r'(:\s?)(")("?[,\]])', r'\1\2\3', result)
    result = re.sub(r'""+"', '""', result)
    return result


class Event:
    def __init__(self, data: Namespace, card):
        self.data = data
        self.card = card
        self.config = get_configuration(card)

    def list(self) -> int:
        try:
            contract_config = get_configuration(self.card)[
                "hidden"]["eth"]["contract"][self.data.alias]
        except KeyError:
            print("There are no contracts with this name")
            return 1

        config = get_configuration(self.card)

        try:
            network = self.data.network.upper()
        except AttributeError:
            try:
                network = contract_config["network"].upper()
            except KeyError:
                network = config["eth"]["network"].upper()

        try:
            endpoint = wallet.Api(config["eth"]["endpoint"], network, config["eth"]["api_key"])
        except ValueError as error:
            print(error)
            return -1

        try:
            abi = _abi(contract_config["abi"])
        except ValueError as error:
            print(error)
            return 3

        contract_endpoint = endpoint.contract(address=contract_config["address"], abi=abi)

        tabulate_table = []
        for event in contract_endpoint.abi:
            if event["type"] == "event":
                args = [[f"{arg['name']}:", arg["type"]] for arg
                        in event.get("inputs")]
                row = [event.get("name"), tabulate(args, tablefmt="plain")]
                tabulate_table.append(row)
        if tabulate_table:
            tabulate_header = ["EVENTS", "ARGUMENTS"]
            print(tabulate(tabulate_table, tabulate_header, tablefmt="grid"))
        return 0

    def logs(self):
        try:
            config_contract = get_configuration(self.card)["hidden"]["eth"]["contract"][self.data.alias]
        except KeyError:
            print("There are no contracts with this name")
            return 1

        config_eth = get_configuration(self.card)["eth"]

        try:
            network = self.data.network.upper()
        except AttributeError:
            try:
                network = config_contract["network"].upper()
            except KeyError:
                network = config_eth["network"].upper()

        try:
            endpoint = wallet.Api(config_eth["endpoint"], network, config_eth["api_key"])
        except ValueError as error:
            print(error)
            return -1

        try:
            abi = _abi(config_contract["abi"])
        except ValueError as error:
            print(error)
            return 3

        contract_endpoint = endpoint.contract(address=config_contract["address"], abi=abi)

        try:
            event = getattr(contract_endpoint.events, self.data.event)
        except web3.exceptions.ABIEventFunctionNotFound:
            print("The event is not defined")
            return 1

        try:
            entries = Event._get_logs(event)
        except ValueError as error:
            print(f"Error in getting the events: {error}")
            return -1
        if entries:
            tabulate_data = Event._logs_table(entries)
            header = ["", "ARGUMENTS", "TRANSACTION HASH", "BLOCK"]
            print(tabulate(tabulate_data, headers=header, tablefmt="grid"))
        else:
            print("No events have been found")
        self.config["hidden"]["eth"]["contract"][self.data.alias][self.data.event] = \
            endpoint.block_number
        save_to_config(self.card, self.config)

        return None

    @staticmethod
    def _get_logs(event) -> List[Dict[str, Any]]:
        min_offset = 0
        max_offset = MONTH_PERIOD_IN_BLOCKS
        offset = _BLOCK_OFFSET

        current_block = event.w3.eth.block_number
        event_signature = event.w3.keccak(
            text=event.abi["name"] + "(" + ",".join([i["type"] for i in event.abi["inputs"]]) + ")"
        )

        decoded_logs = []

        while True:
            filter_params = {
                "fromBlock": hex(current_block - offset),
                "toBlock": hex(current_block),
                "topics": [event_signature],
                "address": event.address,
            }

            try:
                logs = event.w3.eth.get_logs(filter_params)  # Stateless retrieval of logs
                for log in logs:
                    try:
                        decoded_logs.append(event.process_log(log))
                    except Exception as e:
                        print(f"Error decoding log: {e}")
            except ValueError as error:
                if isinstance(error.args[0], dict) and error.args[0].get("code") != MORE_THAN_X_RESULTS:
                    raise
                max_offset = offset = ((max_offset - min_offset) // 2) + min_offset
            else:
                if len(decoded_logs) > 25 or offset >= MONTH_PERIOD_IN_BLOCKS:
                    break
                if max_offset == MONTH_PERIOD_IN_BLOCKS:
                    min_offset = offset
                    offset *= 2
                else:
                    min_offset = offset = ((max_offset - min_offset) // 2) + min_offset

        return list(map(dict, decoded_logs[-25:][::-1]))

    @staticmethod
    def _logs_table(entries):
        tabulate_table = []
        for index, entry in enumerate(entries):
            entry = dict(entry)
            args = "\n".join(f"{name}: {value}" for name, value in
                             entry["args"].items())
            transaction_hash = '0x' + entry["transactionHash"].hex()
            if not _large_screen():
                half_hash_length = int(len(transaction_hash) / 2)
                transaction_hash = \
                    f"{transaction_hash[:half_hash_length]}\n" \
                    f"{transaction_hash[half_hash_length:]}"
            tabulate_table.append(
                [index + 1, args, transaction_hash, entry["blockNumber"]])
        return tabulate_table


class Contract(Command):
    _name = "contract"

    def _execute(self, card):
        try:
            if self.data.contract_action == "add":
                return self._add(card)
            if self.data.contract_action == "call":
                return self._call(card)
            if self.data.contract_action == "list":
                if self.data.alias and not self.data.event:
                    return self._functions(card)
                elif self.data.alias and self.data.event:
                    event = Event(self.data, card)
                    return event.list()
                else:
                    return Contract._list(card)
            if self.data.contract_action == "list_events":
                event = Event(self.data, card)
                return event.logs()
            if self.data.contract_action == "transact":
                return self._transact(card)
        except ApiKeyException as error:
            print(error)
            return -1

        return None

    def _get_endpoint(self, card):
        config = get_configuration(card)

        try:
            network = self.data.network.upper()
        except AttributeError:
            try:
                network = config["hidden"]["eth"]["contract"][self.data.alias][
                    "network"].upper()
            except KeyError:
                network = config["eth"]["network"].upper()

        return wallet.Api(config["eth"]["endpoint"], network, config["eth"]["api_key"])

    def _add(self, card):
        abi = _get_processed_json_argument(self.data.abi)

        try:
            abi_to_config = json.loads(abi)
        except json.decoder.JSONDecodeError as error:
            try:
                abi_to_config = int(abi)
            except ValueError:
                print(f"Error in json: {error}")
                return -1

        try:
            abi = _abi(abi)
        except ValueError:
            print("ERC not recognized by the application.")
            return -1

        try:
            endpoint = self._get_endpoint(card)
        except ValueError as error:
            print(error)
            return -1

        try:
            endpoint.contract(address=self.data.address, abi=abi)
        except web3.exceptions.InvalidAddress as error:
            print(error.args[0])
            return -1

        config = get_configuration(card)
        config["hidden"]["eth"]["contract"][self.data.alias] = {
            "address": self.data.address,
            "abi": abi_to_config,
            "network": endpoint.network.name,
            "block": endpoint.block_number
        }
        save_to_config(card, config)
        print(f"Contract added to application. Use it with alias:"
              f" {self.data.alias}")

        return None

    @staticmethod
    def _list(card) -> int:
        config = get_configuration(card)
        print("\n")

        try:
            table = [[a, c['address']] for a, c in config["hidden"]["eth"]["contract"].items()]
        except KeyError:
            print("There are no contracts on the card")
            return 0

        if table:
            print(tabulate(table, headers=("ALIAS", "ADDRESS")))
        else:
            print("There are no contracts on the card")

        return 0

    def _functions(self, card):
        config = get_configuration(card)
        try:
            config = config["hidden"]["eth"]["contract"][self.data.alias]
        except KeyError:
            print("Contract with alias not found")
            return 1

        tabulate_header = ("NAME", "STATE MUTABILITY", "PARAMETERS")

        tabulate_table = []

        try:
            abi = _abi(config["abi"])
        except ValueError as error:
            print(error)
            return 3

        for event in abi:
            if event["type"] == "function":
                args = [[f"{arg['name'].strip('_')}:", arg["type"]] for arg in event.get("inputs")]
                row = [event.get("name"), event.get("stateMutability"),
                       tabulate(args, tablefmt="plain")]
                tabulate_table.append(row)

        print(tabulate(tabulate_table, headers=tabulate_header, tablefmt="grid"))

        return None

    def _call(self, card):
        config = get_configuration(card)
        try:
            config = config["hidden"]["eth"]["contract"][self.data.alias]
        except KeyError:
            print(f'Contract with name {self.data.alias} not found.')
            return -1

        try:
            abi = _abi(config["abi"])
        except ValueError as error:
            print(error)
            return 3

        try:
            contract_endpoint = self._get_endpoint(card).contract(address=config["address"],
                                                                  abi=abi)
        except ValueError as error:
            print(error)
            return -1

        try:
            function = contract_endpoint.get_function_by_name(self.data.function)
        except ValueError as error:
            print(error)
            print("Valid functions are:")
            self._functions(card)
            return 1

        if function.abi["stateMutability"] in ["nonpayable", "payable"]:
            print("For this function you should use Transact as it changes the state of the network.")
            return 4

        try:
            print(function(*self.data.arguments).call())
        except (TypeError, web3.exceptions.BadFunctionCallOutput) as error:
            print(error)
            return 2
        except web3.exceptions.ContractLogicError as error:
            print(f"Error occurred with execution: {error}")
            return -4

        return 0

    def _transact(self, card):
        self._check(card)

        config = get_configuration(card)

        try:
            contract_config = config["hidden"]["eth"]["contract"][self.data.alias]
        except KeyError:
            print(f'Contract "{self.data.alias}" not found.')
            return 2

        try:
            derivation = cryptnox_sdk_py.Derivation[config["eth"]["derivation"]]
        except LookupError:
            print("Derivation value not valid")
            return 1

        try:
            abi = _abi(contract_config["abi"])
        except ValueError as error:
            print(error)
            return 3

        try:
            endpoint = self._get_endpoint(card)
        except ValueError as error:
            print(error)
            return -1

        contract_endpoint = endpoint.contract(address=contract_config["address"], abi=abi)
        try:
            function = contract_endpoint.get_function_by_name(self.data.function)
        except ValueError as error:
            print(error)
            print("Valid functions are:")
            self._functions(card)
            return 1

        if function.abi["stateMutability"] not in ["nonpayable", "payable"]:
            print("For this function you should use call as it only returns a "
                  "value.")
            return 4

        price, limit = contract.gas(endpoint.gas_price, self.data.price, self.data.limit,
                                    contract.LIMIT["contract"])

        path = b"" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else wallet.Api.PATH
        public_key = card.get_public_key(derivation, path=path, compressed=False)

        nonce = endpoint.get_transaction_count(wallet.checksum_address(public_key))

        balance = endpoint.get_balance(wallet.address(public_key))
        if balance - price * limit < 0:
            print("Not enough fund for the transaction")
            return -2

        try:
            set_data = function(*self.data.arguments).build_transaction({
                "nonce": nonce,
                "gasPrice": price,
                "gas": limit
            })
        except TypeError:
            print("Invalid number of arguments")
            return -3
        except web3.exceptions.ContractLogicError as error:
            print(f"Error occurred with execution: {error}")
            return -4

        print("\nSigning with the Cryptnox")
        digest = endpoint.transaction_hash(set_data)
        signature = sign(card, digest, derivation, path=wallet.Api.PATH)

        if not signature:
            print("Error in getting signature")
            return -1

        if not Contract._confirm(public_key, contract_endpoint.address, balance, 0, price, limit):
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

    @staticmethod
    def _confirm(public_key, address, balance, value, price, limit):
        gas_price = web3.Web3.from_wei(price, "ether")
        gas = Decimal(gas_price * limit)
        balance = web3.Web3.from_wei(balance, "ether")
        tabulate_table = [
            ["BALANCE:", f"{balance}", "ETH", "ON", "ACCOUNT:",
             f"{wallet.checksum_address(public_key)}"],
            ["TRANSACTION:", f"{value}", "ETH", "TO", "CONTRACT:",
             f"{address}"],
            ["MAX GAS:", f"{gas}"],
            ["MAX TOTAL:", f"{gas + value}"]
        ]

        floating_points = max(cryptos.wallet_utils.number_of_significant_digits((gas + value)), 8)

        print("\n\n--- Transaction Ready --- \n")
        print(tabulate(tabulate_table, tablefmt='plain', floatfmt=f".{floating_points}f"), "\n")
        conf = input("Confirm ? [y/N] > ")

        return conf.lower() == "y"


class Eth(Command):
    """
    Command for sending payment on Bitcoin and Ethereum networks
    """
    _name = enums.Command.ETH.value

    def _execute(self, card) -> int:
        self._check(card)
        try:
            if self.data.eth_action == "send":
                return self._send(card)
            if self.data.eth_action == "config":
                return create_config_method(card, self.data.key, self.data.value, "eth")
            if self.data.eth_action == "contract":
                contract_instance = Contract(self.data)
                return contract_instance._execute(card)
        except requests.HTTPError as error:
            if error.response.status_code == 401:
                print("Access denied. Check your API key with: eth config api_key")
            else:
                print(f"There was in issue in communication: {error}")
            return -1
        except requests.RequestException as error:
            print(f"There was in issue in communication: {error}")
            return -1

        return 0

    def _send(self, card) -> int:
        if "contract" in self.data and self.data.contract:
            self._send_token(card)
            return 0

        config = get_configuration(card)["eth"]

        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]]
        except KeyError:
            print("Derivation is invalid")
            return 1

        try:
            endpoint = wallet.Api(config["endpoint"], config["network"], config["api_key"])
        except ValueError as error:
            print(error)
            return -1

        price, limit = contract.gas(endpoint.gas_price, self.data.price, self.data.limit)

        print("Sending ETH")
        try:
            # eth path in the current key
            message = self._send_funds(card, derivation, endpoint, self.data.address,
                                       self.data.amount, price, limit)
        except ValueError as error:
            try:
                print(error.args[0].get(
                    "message", "Something went wrong").capitalize())
                return 1
            except (AttributeError, LookupError):
                raise error

        if message.startswith("DONE"):
            print(f"\nTransaction id: {message[6:]}\nBalance might take 30 s to be refreshed.")

        return 0

    @staticmethod
    def _send_funds(card, derivation, endpoint, address, amount, price, limit):
        path = b"" if derivation == cryptnox_sdk_py.Derivation.CURRENT_KEY else wallet.Api.PATH
        public_key = card.get_public_key(derivation, path=path, compressed=False)

        card.derive(path=wallet.Api.PATH)
        from_address = wallet.checksum_address(public_key)
        balance = endpoint.get_balance(from_address)
        max_spendable = balance - price * limit
        if web3.Web3.to_wei(amount, "ether") > max_spendable:
            raise ValueError({"message": "Not enough fund for the tx"})

        sanitized_transaction = dict(
            nonce=endpoint.get_transaction_count(from_address, "pending"),
            gasPrice=price,
            gas=limit,
            to=web3.Web3.to_checksum_address(address),
            value=web3.Web3.to_wei(amount, "ether"),
            data=b''
        )
        print("\nSigning with the Cryptnox")
        digest = endpoint.transaction_hash(sanitized_transaction)

        signature = sign(card, digest, derivation, path=wallet.Api.PATH)

        if not signature:
            print("Error in getting signature")
            return -1

        gas = Decimal(web3.Web3.from_wei(price, "ether") * limit)
        tabulate_table = [
            ["BALANCE:", f"{web3.Web3.from_wei(balance, 'ether')}", "ETH", "ON", "ACCOUNT:",
             f"{wallet.checksum_address(public_key)}"],
            ["TRANSACTION:", f"{amount}", "ETH", "TO", "ACCOUNT:",
             f"{web3.Web3.to_checksum_address(address)}"],
            ["MAX GAS:", f"{gas}"],
            ["MAX TOTAL:", f"{gas + amount}"]
        ]

        floating_points = cryptos.wallet_utils.number_of_significant_digits((gas + amount))

        print("\n\n--- Transaction Ready --- \n")
        print(tabulate(tabulate_table, tablefmt='plain',
                       floatfmt=f".{floating_points}f"), "\n")
        conf = input("Confirm ? [y/N] > ")
        if conf.lower() != "y":
            return "Canceled by the user."
        return "DONE: " + bytes(endpoint.push(sanitized_transaction, signature, public_key)).hex()

    def _send_token(self, card):
        config = get_configuration(card)["eth"]
        try:
            derivation = cryptnox_sdk_py.Derivation[config["derivation"]]
        except LookupError:
            print("Derivation value not valid")
            return 1

        contract.transfer(card, config["endpoint"], config["network"], config["api_key"],
                          self.data.contract, self.data.address, self.data.amount, self.data.price,
                          self.data.limit, derivation)

        return None
