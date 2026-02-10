# -*- coding: utf-8 -*-
"""
A basic BTC wallet library
"""
import math
import json
import re
import urllib.parse
import urllib.request
from enum import Enum
from typing import Union, List, Dict
from urllib.parse import urlparse

from cryptnox_sdk_py import Derivation
from tabulate import tabulate

from .validators import EnumValidator, IntValidator

try:
    from lib import cryptos
    from lib.cryptos.wallet_utils import number_of_significant_digits
except ImportError:
    from ..lib import cryptos
    from ..lib.cryptos.wallet_utils import number_of_significant_digits


class BtcNetworks(Enum):
    """
    Class defining possible Bitcoin networks
    """
    MAINNET = "mainnet"
    TESTNET = "testnet"


class BlockCypherApi:
    """
    BlockCypherApi
    """

    def __init__(self, api_key, network):
        self.apikey = api_key
        self.url = "https://api.blockcypher.com/v1/btc/main/"
        if network.lower() == "testnet":
            self.url = "https://api.blockcypher.com/v1/btc/test3/"
        self.params = {'token': self.apikey}
        self.js_res = []
        self.web_rsc = None

    def _validate_endpoint(self, endpoint: str) -> str:
        """
        Validate and sanitize endpoint to prevent URL manipulation attacks.

        :param endpoint: The endpoint path to validate
        :return: Validated endpoint
        :raises ValueError: If endpoint contains suspicious characters
        """
        # Security: Prevent path traversal and URL manipulation
        if any(char in endpoint for char in ['..', '//', '@', ':', '?', '#']):
            # Allow single forward slashes but not suspicious patterns
            if not all(part.isalnum() or part in ['-', '_'] for part in endpoint.split('/')):
                raise ValueError(f"Invalid endpoint: contains suspicious characters")
        return endpoint

    def get_data(self, endpoint: str, params: Dict = None, data: bytes = None) \
            -> None:
        """

        :rtype: None
        :param endpoint: str
        :param params: dict
        :param data: bytes
        """
        # Security: Validate endpoint before using in URL construction
        endpoint = self._validate_endpoint(endpoint)

        params = params or {}
        parameters = dict(params)
        parameters.update(self.params)
        params_enc = urllib.parse.urlencode(parameters)
        try:
            # Construct full URL and validate it stays within expected domain
            full_url = self.url + endpoint + "?" + params_enc
            parsed = urlparse(full_url)
            if not parsed.hostname or 'blockcypher.com' not in parsed.hostname:
                raise ValueError(f"Invalid URL: must be blockcypher.com domain")

            req = urllib.request.Request(
                full_url,
                headers={'User-Agent': 'Mozilla/5.0'},
                data=data
            )
            self.web_rsc = urllib.request.urlopen(req, timeout=30)
            self.js_res = json.load(self.web_rsc)
            self.web_rsc = None
        except Exception as ex:
            print(ex)
            raise IOError("Error while processing request:\n%s" % (
                    self.url + endpoint + "?" + params_enc
            )) from ex

    def check_api_resp(self) -> None:
        """

        :rtype: None
        """
        if 'error' in self.js_res:
            print(" !! ERROR :")
            raise Exception(self.js_res['error'])
        if 'errors' in self.js_res:
            print(" !! ERRORS :")
            raise Exception(self.js_res['errors'])

    def get_utx_os(self, addr: str, n_conf) -> List:  # n_conf 0 or 1
        """

        :param addr: str
        :param n_conf: int (0 or 1)
        :return: List
        """
        self.get_data("addrs/" + addr, {'unspentOnly': 'true'})
        # translate inputs from blockcypher to pybitcoinlib
        addr_utxos = self.get_key('txrefs')
        if n_conf == 0:
            addr_utxos.extend(self.get_key('unconfirmed_txrefs'))
        sel_utxos = []
        for utxo in addr_utxos:
            sel_utxos.append({
                'value': utxo['value'],
                'output': utxo['tx_hash'] + ":" + str(utxo['tx_output_n'])
            })
        return sel_utxos

    def push_tx(self, tx_hex: str) -> Dict:
        """
        :param tx_hex:
        :return: str
        """
        data_tx = json.dumps({'tx': tx_hex}).encode('ascii')
        self.get_data("txs/push", data=data_tx)
        self.check_api_resp()
        return self.get_key('tx/hash')

    def get_key(self, key_char: str) -> Dict:
        """

        :param key_char:str
        :return: Dict
        """
        out = self.js_res
        path = key_char.split("/")
        for key in path:
            if key.isdigit():
                key = int(key)
            try:
                out = out[key]
            except KeyError:
                out = []

        return out


class BlkHubApi:
    """
    BlkHubApi
    """

    def __init__(self, network):
        network = network.lower()
        self.url = BlkHubApi.get_api(network)
        self.js_res = []
        self.web_rsc = None

    @staticmethod
    def get_api(network: str) -> str:
        """
        Get API url for given network

        :param str network:
        :return: API url
        :rtype: str
        """
        if network.lower() == "mainnet":
            return "https://blkhub.net/api/"
        if network.lower() == "testnet":
            return "https://blockstream.info/testnet/api/"
        raise Exception("Unknown BC network name")

    def _validate_endpoint(self, endpoint: str) -> str:
        """
        Validate and sanitize endpoint to prevent URL manipulation attacks.

        :param endpoint: The endpoint path to validate
        :return: Validated endpoint
        :raises ValueError: If endpoint contains suspicious characters
        """
        # Security: Prevent path traversal and URL manipulation
        if any(char in endpoint for char in ['..', '//', '@', ':', '?', '#']):
            # Allow single forward slashes but not suspicious patterns
            if not all(part.isalnum() or part in ['-', '_'] for part in endpoint.split('/')):
                raise ValueError(f"Invalid endpoint: contains suspicious characters")
        return endpoint

    def get_data(self, endpoint: str, params: Dict = None, data: bytes = None) \
            -> None:
        """

        :param endpoint: str
        :param params: dict
        :param data: bytes
        :return: None
        """
        # Security: Validate endpoint before using in URL construction
        endpoint = self._validate_endpoint(endpoint)

        params = params or {}
        parameters = dict(params)
        params_enc = urllib.parse.urlencode(parameters)
        try:
            # Construct full URL and validate it stays within expected domain
            full_url = self.url + endpoint + "?" + params_enc
            parsed = urlparse(full_url)
            if not parsed.hostname or not any(domain in parsed.hostname
                                             for domain in ['blkhub.net', 'blockstream.info']):
                raise ValueError(f"Invalid URL: must be blkhub.net or blockstream.info domain")

            req = urllib.request.Request(
                full_url,
                headers={'User-Agent': 'Mozilla/5.0'},
                data=data
            )
            self.web_rsc = urllib.request.urlopen(req, timeout=30)
            b_rep = self.web_rsc.read()
            if len(b_rep) == 64 and b_rep[0] != ord('{'):
                b_rep = b'{"txid":"' + b_rep + b'"}'
            self.js_res = json.loads(b_rep)
        except urllib.error.HTTPError as error:
            raise IOError(f"Error while processing request:\n{error.code} - "
                          f"{error.read().decode('utf8')}") from error
        except Exception as error:
            raise IOError(f"Error while processing request:\n{self.url}{endpoint}?params_enc\n"
                          f"{error}") from error

    def check_api_resp(self) -> None:
        """

        :rtype: None
        """
        if 'error' in self.js_res:
            print(" !! ERROR :")
            raise Exception(self.js_res['error'])
        if 'errors' in self.js_res:
            print(" !! ERRORS :")
            raise Exception(self.js_res['errors'])

    def get_fee_estimates(self, blocks=6) -> int:
        self.get_data("fee-estimates")
        block_entries = [int(x) for x in self.js_res.keys() if int(x) <= blocks]
        block_entries.sort()
        try:
            return math.ceil(self.js_res[str(block_entries.pop())])
        except KeyError:
            return 0

    def get_utx_os(self, addr: str, _n_conf: int) -> List:
        """

        :param addr:str
        :param int _n_conf: 0 or 1
        :return: list
        """
        self.get_data("address/" + addr + "/utxo")
        addr_utx_os = self.js_res
        sel_utx_os = []
        # translate inputs from blkhub to pybitcoinlib
        for utxo in addr_utx_os:
            sel_utx_os.append({
                'value': utxo['value'],
                'output': utxo['txid'] + ":" + str(utxo['vout'])
            })
        return sel_utx_os

    def push_tx(self, tx_hex: str) -> List:
        """

        :param tx_hex: str
        :return: List
        """
        self.get_data("tx", data=tx_hex.encode('ascii'))
        self.check_api_resp()
        return self.get_key('txid')

    def get_key(self, key_char: str) -> List:
        """

        :param key_char: str
        :return: list
        """
        out = self.js_res
        path = key_char.split("/")
        for key in path:
            if key.isdigit():
                key = int(key)
            try:
                out = out[key]
            except LookupError:
                out = []
        return out


def test_addr(btc_addr: str):
    """

    :param btc_addr: str
    :return:
    """
    # Safe test of the address format
    if btc_addr.startswith("1") or btc_addr.startswith("3"):
        return re.match('^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', btc_addr)
    if btc_addr.startswith("n") or btc_addr.startswith(
            "m") or btc_addr.startswith("2"):
        return re.match('^[2nm][a-km-zA-HJ-NP-Z1-9]{25,34}$', btc_addr)

    return False


class BTCwallet:
    """
    BTCwallet
    """
    PATH = "m/44'/0'/0'/0/0"

    def __init__(self, pubkey: str, coin_type: str, api,
                 card) -> None:
        """
        :param pubkey: str
        :param coin_type: str
        :param api:
        :param connection:
        """
        addr_header = 0x00
        self.testnet = False
        coin_type = coin_type.lower()
        if coin_type == "testnet":
            addr_header = 0x6F
            self.testnet = True
        self.pubkey = pubkey
        pkh = cryptos.bin_hash160(bytes.fromhex(pubkey))
        self.address = cryptos.bin_to_b58check(pkh, addr_header)
        self.api = api
        self.card = card
        self.balance = None
        self.var_tx = None
        self.len_inputs = None
        self.data_hash = []
        self.fee = 2000

    def get_utx_os(self, n_conf: int = 0):
        """
        :param n_conf: int (0 or 1)
        :return:
        """
        return self.api.get_utx_os(self.address, n_conf)

    def get_balance(self) -> float:
        """

        :return: float
        """
        utx_os = self.get_utx_os()
        return self.balance_fm_utxos(utx_os)

    def get_fee_estimate(self):
        return self.api.get_fee_estimate()

    def prepare(self, to_addr: str, payment_value: float, fee: float) \
            -> Union[float, int]:
        """

        :param to_addr: str
        :param payment_value: float
        :param fee: float
        :return: Union[float, int]
        """
        self.fee = fee

        if not test_addr(to_addr):
            raise Exception("Bad address format.")
        utx_os = self.get_utx_os()
        balance = self.balance_fm_utxos(utx_os)
        self.balance = balance / 10.0 ** 8
        max_spendable = balance - fee
        if payment_value > max_spendable:
            raise Exception("Not enough fund for the tx")
        inputs = self.select_utxos(payment_value + fee, utx_os)
        in_value = self.balance_fm_utxos(inputs)
        change_value = in_value - payment_value - fee
        outs = [{'value': payment_value, 'address': to_addr}]
        if change_value > 0:
            outs.append({'value': change_value, 'address': self.address})
        self.var_tx = cryptos.coins.bitcoin.Bitcoin(testnet=self.testnet). \
            mktx(inputs, outs)
        script = cryptos.mk_pubkey_script(self.address)
        # Finish tx
        # Sign each input
        self.len_inputs = len(inputs)
        for i in range(self.len_inputs):
            signing_tx = cryptos.signature_form(self.var_tx, i, script, cryptos.SIGHASH_ALL)
            self.data_hash.append(cryptos.bin_txhash(signing_tx, cryptos.SIGHASH_ALL))
        return 0

    def send(self, to_addr: str, payment_value: float, signature: List[bytes]) -> str:
        """

        :param to_addr: str
        :param payment_value: float
        :return: str
        """
        # Cryptnox Sign
        for i in range(0, self.len_inputs):
            self.var_tx["ins"][i]["script"] = cryptos.serialize_script([signature[i].hex() + "01", self.pubkey])

        tabulate_table = [
            ["BALANCE:", f"{self.balance}", "BTC", "ON", "ACCOUNT:",
             f"{self.address}"],
            ["TRANSACTION:", f"{payment_value / 10 ** 8}", "BTC", "FROM",
             "ACCOUNT:", f"{to_addr}"],
            ["FEE:", f"{self.fee / 10 ** 8}"],
            ["TOTAL:", (self.fee + payment_value) / 10 ** 8]
        ]

        floating_points = number_of_significant_digits(
            (self.fee + payment_value) / 10 ** 8)

        print("\n\n--- Transaction Ready ---\n")
        print(tabulate(tabulate_table, tablefmt='plain',
                       floatfmt=f".{floating_points}f"), "\n")
        conf = input("Confirm ? [y/N] > ")
        if conf.lower() == "y":
            tx_hex = cryptos.serialize(self.var_tx)
            return "\nDONE, txID : " + self.api.push_tx(tx_hex)
        return "Canceled by the user."

    @staticmethod
    def balance_fm_utxos(utxos) -> float:
        """

        :param utxos:
        :return: float
        """
        bal = 0
        for utxo in utxos:
            bal += utxo['value']
        return bal

    @staticmethod
    def select_utxos(amount: float, utxos) -> List:
        """

        :param amount: float
        :param utxos:
        :return: float
        """
        sorted_utxos = sorted(utxos, key=lambda x: x['value'], reverse=True)
        sel_utxos = []
        for s_utxo in sorted_utxos:
            amount -= s_utxo['value']
            sel_utxos.append(s_utxo)
            if amount <= 0:
                break
        if amount <= 0:
            return sel_utxos
        raise Exception("Not enough utxos values for the tx")


class BtcValidator:
    """
    Class defining Bitcoin validators
    """
    network = EnumValidator(BtcNetworks)
    fees = IntValidator()
    derivation = EnumValidator(Derivation)

    def __init__(self, network: str = "testnet", fees: int = 2000,
                 derivation: str = "DERIVE"):
        self.network = network
        self.fees = fees
        self.derivation = derivation
