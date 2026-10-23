"""
Module for monitoring and notifying users about ERC token activities,
transaction events, and other blockchain-related notifications using
multiprocessing for efficient parallel processing.
"""

import json
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, Any

import requests as requests

try:
    from config import (
        get_cached_serials,
        get_configuration
    )
    from wallet import eth as wallet
except ImportError:
    from ...config import (
        get_cached_serials,
        get_configuration
    )
    from ...wallet import eth as wallet

ERC_PATH = Path(__file__).parent.parent.parent.joinpath("contract_abi")
MORE_THAN_X_RESULTS = -32005
MONTH_PERIOD_IN_BLOCKS = 4 * 30 * 24 * 60 * 4  # average of 15 s


def _erc_abi_file(value):
    return ERC_PATH.joinpath(f"erc{value}.json").absolute()


def _abi(config) -> Dict[str, Any]:
    try:
        path = _erc_abi_file(int(config))
    except TypeError:
        return config

    try:
        abi = json.loads(path.read_text())
    except (FileNotFoundError, PermissionError,
            json.decoder.JSONDecodeError):
        raise ValueError("ERC not recognized by the application.")

    return abi


class Notification:
    def __init__(self):
        self.pool = Pool(processes=10)
        self.work = None
        self.last_checks = {}

    @staticmethod
    def _check(data):
        import web3

        try:
            w3 = wallet.Web3Api(None,
                                wallet.endpoint_factory(data["endpoint"], data["network"],
                                                        data["api_key"])).web3
            contract = w3.eth.contract(address=data["address"], abi=data["abi"])
            event = contract.events[data["event_name"]]

            event_filter = event.createFilter(fromBlock=data["from_block"],
                                              toBlock=data["to_block"])
            try:
                data["count"] = len(event_filter.get_all_entries())
            except web3.exceptions.LogTopicError:
                data["count"] = -1
            except ValueError as error:
                if error.args[0]["code"] == MORE_THAN_X_RESULTS:
                    data["count"] = "More than 10 000 results"
                else:
                    raise
        except Exception as error:
            print(error)

        return data

    def run(self):
        if self.work:
            return

        data = []
        for serial in get_cached_serials():
            config = get_configuration(serial)
            contract_config = config["hidden"]["eth"]["contract"]
            for alias, contract_config in contract_config.items():
                alias_config = contract_config[alias]
                network_name = contract_config["network"].upper()

                network = wallet.Web3Api(None, wallet.endpoint_factory(config["endpoint"],
                                                                       network_name,
                                                                       config["api_key"]))
                w3 = network.web3
                contract = w3.eth.contract(
                    address=contract_config["address"],
                    abi=_abi(contract_config["abi"]))
                current_block = w3.eth.block_number
                for event in contract.events:
                    last_check = alias_config.get(event,
                                                  current_block - MONTH_PERIOD_IN_BLOCKS)
                    data.append({
                        "serial": serial,
                        "alias": alias,
                        "address": contract_config["address"],
                        "abi": _abi(contract_config["abi"]),
                        "network": contract_config["network"],
                        "endpoint": config["endpoint"],
                        "api_key": config["api_key"],
                        "event_name": event.event_name,
                        "from_block": last_check,
                        "to_block": current_block,
                        "count": -1
                    })

        self.work = self.pool.map_async(Notification._check, data)

    def get(self):
        results = {}
        try:
            self.work.wait()
        except AttributeError:
            return results
        try:
            data = self.work.get()
        except requests.exceptions.HTTPError:
            print("There is an issue reading event notifications.")
            return results
        for entry in data:
            if entry["count"] in [-1, 0]:
                continue

            if entry["serial"] not in results:
                results[entry["serial"]] = {}
            if entry["alias"] not in results[entry["serial"]]:
                results[entry["serial"]][entry["alias"]] = {}
            results[entry["serial"]][entry["alias"]][entry["event_name"]] = \
                entry["count"]

        self.work = None
        return results
