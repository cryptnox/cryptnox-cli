# flake8: noqa
# -*- coding: utf-8 -*-
"""
Block header encoding/decoding utilities and related primitives.
"""
from .main import *


def serialize_header(inp):
    o = encode(inp['version'], 256, 4)[::-1] + \
        inp['prevhash'].decode('hex')[::-1] + \
        inp['merkle_root'].decode('hex')[::-1] + \
        encode(inp['timestamp'], 256, 4)[::-1] + \
        encode(inp['bits'], 256, 4)[::-1] + \
        encode(inp['nonce'], 256, 4)[::-1]
    h = bin_sha256(bin_sha256(o))[::-1].encode('hex')
    assert h == inp['hash'], (sha256(o), inp['hash'])
    return o.encode('hex')


def deserialize_header(inp):
    inp = inp.decode('hex')
    return {
        "version": decode(inp[:4][::-1], 256),
        "prevhash": inp[4:36][::-1].encode('hex'),
        "merkle_root": inp[36:68][::-1].encode('hex'),
        "timestamp": decode(inp[68:72][::-1], 256),
        "bits": decode(inp[72:76][::-1], 256),
        "nonce": decode(inp[76:80][::-1], 256),
        "hash": bin_sha256(bin_sha256(inp))[::-1].encode('hex')
    }


def mk_merkle_proof(header, hashes, index):
    nodes = [safe_from_hex(h)[::-1] for h in hashes]
    if len(nodes) % 2 and len(nodes) > 2:
        nodes.append(nodes[-1])
    layers = [nodes]
    while len(nodes) > 1:
        newnodes = []
        for i in range(0, len(nodes) - 1, 2):
            newnodes.append(bin_sha256(bin_sha256(nodes[i] + nodes[i+1])))
        if len(newnodes) % 2 and len(newnodes) > 2:
            newnodes.append(newnodes[-1])
        nodes = newnodes
        layers.append(nodes)
    # Sanity check, make sure merkle root is valid
    assert bytes_to_hex_string(nodes[0][::-1]) == header['merkle_root']
    merkle_siblings = \
        [layers[i][(index >> i) ^ 1] for i in range(len(layers)-1)]
    return {
        "hash": hashes[index],
        "siblings": [bytes_to_hex_string(x[::-1]) for x in merkle_siblings],
        "header": header
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
    "deserialize_header",
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
    "mk_merkle_proof",
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
    "serialize_header",
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
]
