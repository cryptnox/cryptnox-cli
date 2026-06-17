# flake8: noqa
# -*- coding: utf-8 -*-
"""
Simple wallet abstractions for addresses, balances, and signing flows.

This module is based on code from pybtctools:
https://github.com/primal100/pybitcointools/blob/master/cryptos/wallet.py
"""
from .main import *
from .keystore import xpubkey_to_address


class HDWallet(object):

    def __init__(self, keystore, num_addresses=0, last_receiving_index=0, last_change_index=0):
        self.coin = keystore.coin
        self.keystore = keystore
        self.addresses = {}
        self.last_receiving_index = last_receiving_index
        self.last_change_index = last_change_index
        self.new_receiving_addresses(num=num_addresses)
        self.new_change_addresses(num=num_addresses)
        self.is_watching_only = self.keystore.is_watching_only()
        if self.keystore.electrum:
            self.script_type = self.keystore.xtype
        else:
            self.script_type = "p2pkh"

    def privkey(self, address, formt="wif_compressed", password=None):
        if self.is_watching_only:
            return None
        try:
            addr_derivation = self.addresses[address]
        except KeyError:
            raise Exception(
                "Address %s has not been generated yet. Generate new addresses with new_receiving_addresses or new_change_addresses methods" % address)
        pk, compressed = self.keystore.get_private_key(addr_derivation, password)
        return self.coin.encode_privkey(pk, formt, script_type=self.script_type)

    def export_privkeys(self, password=None):
        if self.is_watching_only:
            return None
        return {
            'receiving': {addr: self.privkey(addr, password=password) for addr in self.receiving_addresses},
            'change': {addr: self.privkey(addr, password=password) for addr in self.change_addresses}
        }

    def pubkey_receiving(self, index):
        return self.keystore.derive_pubkey(0, index)

    def pubkey_change(self, index):
        return self.keystore.derive_pubkey(1, index)

    def pubtoaddr(self, pubkey):
        if self.keystore.xtype == "p2pkh":
            return self.coin.pubtoaddr(pubkey)
        elif self.keystore.xtype == "p2wpkh":
            return self.coin.pubtosegwit(pubkey)
        elif self.keystore.xtype == "p2wpkh-p2sh":
            return self.coin.pubtop2w(pubkey)
        return None

    def receiving_address(self, index):
        pubkey = self.pubkey_receiving(index)
        address = self.pubtoaddr(pubkey)
        self.addresses[address] = (0, index)
        return address

    def change_address(self, index):
        pubkey = self.pubkey_change(index)
        address = self.pubtoaddr(pubkey)
        self.addresses[address] = (1, index)
        return address

    @property
    def receiving_addresses(self):
        return [addr for addr in self.addresses.keys() if not self.addresses[addr][0]]

    @property
    def change_addresses(self):
        return [addr for addr in self.addresses.keys() if self.addresses[addr][0]]

    def new_receiving_address_range(self, num):
        index = self.last_receiving_index
        return range(index, index+num)

    def new_change_address_range(self, num):
        index = self.last_change_index
        return range(index, index+num)

    def new_receiving_addresses(self, num=10):
        addresses = list(map(self.receiving_address, self.new_receiving_address_range(num)))
        self.last_receiving_index += num
        return addresses

    def new_change_addresses(self, num=10):
        addresses = list(map(self.change_address, self.new_change_address_range(num)))
        self.last_change_index += num
        return addresses

    def new_receiving_address(self):
        return self.new_receiving_addresses(num=1)[0]

    def new_change_address(self):
        return self.new_change_addresses(num=1)[0]

    def balance(self):
        raise NotImplementedError

    def unspent(self):
        raise NotImplementedError

    def select(self):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def sign(self, tx, password=None):
        if self.is_watching_only:
            return
        raise NotImplementedError

    def mksend(self, outs):
        raise NotImplementedError

    def sign_message(self, message, address, password=None):
        if self.is_watching_only:
            return
        raise NotImplementedError

    def is_mine(self, address):
        return address in self.addresses.keys()

    def is_change(self, address):
        return address in self.change_addresses

    def account(self, address, password=None):
        derivation = self.addresses[address][0]
        privkey = self.privkey(address, formt="wif_compressed", password=password)
        pub = self.coin.privtopub(privkey)
        derivation = "%s/%s'/%s" % (self.keystore.root_derivation, derivation[0], derivation[1])
        return (derivation, privkey, pub, address)

    def details(self, password=None):
        return {
            'type': "%s %s" % ("Electrum" if self.keystore.electrum else "BIP39", self.keystore.xtype),
            'xkeys': (self.keystore.root_derivation, self.keystore.xpriv, self.keystore.xpub),
            'xreceiving': (),
            'xchange': (),
            'receiving': [self.account(a, password=password) for a in self.receiving_addresses],
            'change': [self.account(a, password=password) for a in self.change_addresses]
        }


# Explicit public API (added to satisfy CodeQL py/polluting-import).
# Lists the names this module already exported via 'import *', so wildcard
# import behaviour is unchanged.
__all__ = [
    "A",
    "B",
    "F0",
    "F1",
    "F2",
    "F3",
    "F4",
    "G",
    "Gx",
    "Gy",
    "HDWallet",
    "K0",
    "K1",
    "K2",
    "K3",
    "K4",
    "KK0",
    "KK1",
    "KK2",
    "KK3",
    "KK4",
    "N",
    "P",
    "PADDING",
    "R",
    "RIPEMD160",
    "RMD160Final",
    "RMD160Transform",
    "RMD160Update",
    "RMDContext",
    "ROL",
    "access",
    "add",
    "add_privkeys",
    "add_pubkeys",
    "b58check_to_bin",
    "b58check_to_hex",
    "base64",
    "bin_dbl_sha256",
    "bin_hash160",
    "bin_ripemd160",
    "bin_sha256",
    "bin_slowsha",
    "bin_to_b58check",
    "binascii",
    "bytes_to_hex_string",
    "change_curve",
    "changebase",
    "code_strings",
    "compress",
    "count",
    "dbl_sha256",
    "decode",
    "decode_privkey",
    "decode_pubkey",
    "decode_sig",
    "decompress",
    "deterministic_generate_k",
    "digest_size",
    "digestsize",
    "divide",
    "ecdsa_raw_recover",
    "ecdsa_raw_sign",
    "ecdsa_raw_verify",
    "ecdsa_recover",
    "ecdsa_sign",
    "ecdsa_verify",
    "ecdsa_verify_addr",
    "electrum_sig_hash",
    "encode",
    "encode_privkey",
    "encode_pubkey",
    "encode_sig",
    "fast_add",
    "fast_multiply",
    "from_byte_to_int",
    "from_int_representation_to_bytes",
    "from_int_to_byte",
    "from_jacobian",
    "from_string_to_bytes",
    "getG",
    "get_code_string",
    "get_privkey_format",
    "get_pubkey_format",
    "get_version_byte",
    "hash160",
    "hash160High",
    "hash160Low",
    "hash_to_int",
    "hashlib",
    "hex_to_b58check",
    "hex_to_hash160",
    "hmac",
    "int_types",
    "inv",
    "is_privkey",
    "is_pubkey",
    "is_python2",
    "isinf",
    "jacobian_add",
    "jacobian_double",
    "jacobian_multiply",
    "lpad",
    "magicbyte_to_prefix",
    "mul_privkeys",
    "multiaccess",
    "multiply",
    "neg_privkey",
    "neg_pubkey",
    "new",
    "num_to_var_int",
    "os",
    "privkey_to_address",
    "privkey_to_pubkey",
    "privtoaddr",
    "privtopub",
    "pubkey_to_address",
    "pubkey_to_hash",
    "pubkey_to_hash_hex",
    "pubtoaddr",
    "random",
    "random_electrum_seed",
    "random_key",
    "random_string",
    "re",
    "ripemd160",
    "safe_from_hex",
    "safe_hexlify",
    "sha256",
    "slice",
    "slowsha",
    "string_or_bytes_types",
    "string_types",
    "struct",
    "subtract",
    "subtract_privkeys",
    "subtract_pubkeys",
    "sum",
    "sys",
    "time",
    "to_jacobian",
    "xpubkey_to_address",
]
