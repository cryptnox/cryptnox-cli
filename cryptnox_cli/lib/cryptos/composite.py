# flake8: noqa
# -*- coding: utf-8 -*-
"""
High-level composition utilities combining deterministic keys and transactions.
"""
from .deterministic import *
from .transaction import *
from .main import *


# BIP32 hierarchical deterministic multisig script
def bip32_hdm_script(*args):
    if len(args) == 3:
        keys, req, path = args
    else:
        i, keys, path = 0, [], []
        while len(args[i]) > 40:
            keys.append(args[i])
            i += 1
        req = int(args[i])
        path = map(int, args[i+1:])
    pubs = sorted(map(lambda x: bip32_descend(x, path), keys))
    return mk_multisig_script(pubs, req)


# BIP32 hierarchical deterministic multisig address
def bip32_hdm_addr(*args):
    return scriptaddr(bip32_hdm_script(*args))


# Setup a coinvault transaction
def setup_coinvault_tx(tx, script):
    txobj = deserialize(tx)
    N = deserialize_script(script)[-2]
    for inp in txobj["ins"]:
        inp["script"] = serialize_script([None] * (N+1) + [script])
    return serialize(txobj)


# Sign a coinvault transaction
def sign_coinvault_tx(tx, priv):
    pub = privtopub(priv)
    txobj = deserialize(tx)
    subscript = deserialize_script(txobj['ins'][0]['script'])
    oscript = deserialize_script(subscript[-1])
    k, pubs = oscript[0], oscript[1:-2]
    for j in range(len(txobj['ins'])):
        scr = deserialize_script(txobj['ins'][j]['script'])
        for i, p in enumerate(pubs):
            if p == pub:
                scr[i+1] = multisign(tx, j, subscript[-1], priv)
        if len(filter(lambda x: x, scr[1:-1])) >= k:
            scr = [None] + filter(lambda x: x, scr[1:-1])[:k] + [scr[-1]]
        txobj['ins'][j]['script'] = serialize_script(scr)
    return serialize(txobj)


# Explicit public API (added to satisfy CodeQL py/polluting-import).
# Lists the names this module already exported via 'import *', so wildcard
# import behaviour is unchanged.
__all__ = [
    "A",
    "B",
    "DEFAULT",
    "F0",
    "F1",
    "F2",
    "F3",
    "F4",
    "G",
    "Gx",
    "Gy",
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
    "MAINNET_PRIVATE",
    "MAINNET_PUBLIC",
    "N",
    "P",
    "PADDING",
    "PRIVATE",
    "PUBLIC",
    "R",
    "RIPEMD160",
    "RMD160Final",
    "RMD160Transform",
    "RMD160Update",
    "RMDContext",
    "ROL",
    "SIGHASH_ALL",
    "SIGHASH_ANYONECANPAY",
    "SIGHASH_FORKID",
    "SIGHASH_NONE",
    "SIGHASH_SINGLE",
    "TESTNET_PRIVATE",
    "TESTNET_PUBLIC",
    "access",
    "add",
    "add_privkeys",
    "add_pubkeys",
    "apply_multisignatures",
    "b58check_to_bin",
    "b58check_to_hex",
    "base64",
    "bin_dbl_sha256",
    "bin_hash160",
    "bin_ripemd160",
    "bin_sha256",
    "bin_slowsha",
    "bin_to_b58check",
    "bin_txhash",
    "binascii",
    "bip32_bin_extract_key",
    "bip32_ckd",
    "bip32_derive_key",
    "bip32_descend",
    "bip32_deserialize",
    "bip32_extract_key",
    "bip32_hdm_addr",
    "bip32_hdm_script",
    "bip32_master_key",
    "bip32_privtopub",
    "bip32_serialize",
    "bytes_to_hex_string",
    "change_curve",
    "changebase",
    "code_strings",
    "coinvault_priv_to_bip32",
    "coinvault_pub_to_bip32",
    "compress",
    "copy",
    "count",
    "crack_bip32_privkey",
    "crack_electrum_wallet",
    "dbl_sha256",
    "dbl_sha256_list",
    "decode",
    "decode_privkey",
    "decode_pubkey",
    "decode_sig",
    "decompress",
    "der_decode_sig",
    "der_encode_sig",
    "deserialize",
    "deserialize_script",
    "deterministic_generate_k",
    "digest_size",
    "digestsize",
    "divide",
    "ecdsa_raw_recover",
    "ecdsa_raw_sign",
    "ecdsa_raw_verify",
    "ecdsa_recover",
    "ecdsa_sign",
    "ecdsa_tx_recover",
    "ecdsa_tx_sign",
    "ecdsa_tx_verify",
    "ecdsa_verify",
    "ecdsa_verify_addr",
    "electrum_address",
    "electrum_mpk",
    "electrum_privkey",
    "electrum_pubkey",
    "electrum_sig_hash",
    "electrum_stretch",
    "encode",
    "encode_1_byte",
    "encode_4_bytes",
    "encode_8_bytes",
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
    "is_bip66",
    "is_inp",
    "is_privkey",
    "is_pubkey",
    "is_python2",
    "is_segwit",
    "is_xprv",
    "is_xpub",
    "isinf",
    "jacobian_add",
    "jacobian_double",
    "jacobian_multiply",
    "json_changebase",
    "json_is_base",
    "list_to_bytes",
    "lpad",
    "magicbyte_to_prefix",
    "mk_multisig_script",
    "mk_p2w_scripthash_script",
    "mk_p2wpkh_redeemscript",
    "mk_p2wpkh_script",
    "mk_p2wpkh_scriptcode",
    "mk_pubkey_script",
    "mk_scripthash_script",
    "mul_privkeys",
    "multiaccess",
    "multiply",
    "multisign",
    "neg_privkey",
    "neg_pubkey",
    "new",
    "num_to_var_int",
    "os",
    "output_script_to_address",
    "p2wpkh_nested_script",
    "parse_bip32_path",
    "privkey_to_address",
    "privkey_to_pubkey",
    "privtoaddr",
    "privtopub",
    "pubkey_to_address",
    "pubkey_to_hash",
    "pubkey_to_hash_hex",
    "public_txhash",
    "pubtoaddr",
    "random",
    "random_electrum_seed",
    "random_key",
    "random_string",
    "raw_bip32_ckd",
    "raw_bip32_privtopub",
    "raw_crack_bip32_privkey",
    "re",
    "reduce",
    "ripemd160",
    "safe_from_hex",
    "safe_hexlify",
    "select",
    "serialize",
    "serialize_script",
    "serialize_script_unit",
    "setup_coinvault_tx",
    "sha256",
    "sign_coinvault_tx",
    "signature_form",
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
    "txhash",
    "uahf_digest",
    "verify_tx_input",
]
