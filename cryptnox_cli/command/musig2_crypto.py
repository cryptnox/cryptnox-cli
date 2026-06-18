# -*- coding: utf-8 -*-
"""
Host-side cryptography for MuSig2 (BIP-327) signing with Cryptnox Basic G2 cards.

The Cryptnox Basic G2 card performs the secret-dependent part of a MuSig2
signature (nonce generation and the partial signature) inside the secure
element.  Everything that does not require the private key -- public-key and
nonce aggregation (BIP-327), the BIP-340 Schnorr challenge, the BIP-341 Taproot
tweak and address derivation, transaction serialisation and signature
verification -- is done here on the host.

The exact algorithm and the byte layout of the data exchanged with the card
mirror the reference scripts in the ``cryptnox-cli-musig2`` repository (the
"oracle"), which were validated against the card firmware.  This module
deliberately reproduces that math, including the places where it differs from a
strict BIP-327 implementation, so the host stays compatible with the applet.

All elliptic-curve operations reuse the secp256k1 primitives that already ship
with the CLI (``cryptnox_cli.lib.cryptos.main``) so no extra dependency such as
``coincurve`` is required.
"""

import hashlib
import struct

try:
    from lib import cryptos
except ImportError:
    from ..lib import cryptos

# secp256k1 group order, field prime and generator (from the bundled cryptos lib)
N = cryptos.N
P = cryptos.P
G = cryptos.G


# ============================================================
# Tagged hash (BIP340 / BIP341 / BIP327)
# ============================================================

def tagged_hash(tag: str, msg: bytes) -> bytes:
    """Return the BIP-340 tagged hash ``SHA256(SHA256(tag)||SHA256(tag)||msg)``."""
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + msg).digest()


# ============================================================
# EC point helpers -- points are (x, y) integer tuples
# ============================================================

def point_from_bytes(data: bytes):
    """Decode a compressed (33B), uncompressed (65B) or raw (64B) public key."""
    return cryptos.decode_pubkey(data)


def point_to_compressed(point) -> bytes:
    """Encode an (x, y) point as a 33-byte compressed public key."""
    return cryptos.encode_pubkey(point, "bin_compressed")


def point_to_uncompressed(point) -> bytes:
    """Encode an (x, y) point as a 65-byte uncompressed public key."""
    return cryptos.encode_pubkey(point, "bin")


def point_add(point_a, point_b):
    """Add two secp256k1 points."""
    return cryptos.fast_add(point_a, point_b)


def point_mul(point, scalar: int):
    """Multiply a secp256k1 point by a scalar."""
    return cryptos.fast_multiply(point, scalar)


def point_add_bytes(points):
    """Add a list of public keys given as bytes, returning an (x, y) point."""
    decoded = [point_from_bytes(p) for p in points]
    acc = decoded[0]
    for point in decoded[1:]:
        acc = cryptos.fast_add(acc, point)
    return acc


def point_mul_bytes(pk_bytes: bytes, scalar: int):
    """Multiply the public key ``pk_bytes`` by ``scalar``, returning an (x, y) point."""
    return cryptos.fast_multiply(point_from_bytes(pk_bytes), scalar)


def compressed_pubkey(card_response: bytes) -> bytes:
    """Normalise a card public-key response to 33-byte compressed form."""
    return point_to_compressed(point_from_bytes(card_response))


def xonly(compressed: bytes) -> bytes:
    """Return the x-only (32-byte) part of a compressed public key."""
    return compressed[1:33]


def has_even_y(compressed: bytes) -> bool:
    """True when the compressed public key encodes an even-y point (prefix 0x02)."""
    return compressed[0] == 0x02


def lift_x(x_bytes: bytes) -> bytes:
    """Return the compressed even-y public key with the given x coordinate."""
    return b"\x02" + x_bytes


def negate_compressed(pk33: bytes) -> bytes:
    """Negate a point by flipping the parity byte of its compressed encoding."""
    prefix = b"\x03" if pk33[0] == 0x02 else b"\x02"
    return prefix + pk33[1:]


# ============================================================
# BIP327 key and nonce aggregation
# ============================================================

def keyagg_coeff(key_list_hash: bytes, pk: bytes) -> int:
    """KeyAgg coefficient for ``pk`` given the tagged hash of the key list."""
    digest = tagged_hash("KeyAgg coefficient", key_list_hash + pk)
    return int.from_bytes(digest, "big") % N


def aggregate_pubkey(sorted_pks):
    """
    Aggregate the (already sorted) list of 33-byte compressed public keys.

    :return: tuple of (compressed aggregate key, x-only aggregate key)
    """
    key_list_hash = tagged_hash("KeyAgg list", b"".join(sorted_pks))
    acc = None
    for pk in sorted_pks:
        coeff = keyagg_coeff(key_list_hash, pk)
        term = point_mul_bytes(pk, coeff)
        acc = term if acc is None else point_add(acc, term)
    compressed = point_to_compressed(acc)
    return compressed, xonly(compressed)


def nonce_coeff(aggnonce: bytes, aggpubkey_x: bytes, msg: bytes) -> int:
    """BIP-327 nonce coefficient ``b``."""
    digest = tagged_hash("MuSig/noncecoef", aggnonce + aggpubkey_x + msg)
    return int.from_bytes(digest, "big") % N


def aggregate_nonces(nonces_r1, nonces_r2):
    """
    Aggregate per-card nonce points.

    :param nonces_r1: list of 33-byte first-round nonce points
    :param nonces_r2: list of 33-byte second-round nonce points
    :return: tuple (aggR1_point, aggR2_point)
    """
    return point_add_bytes(nonces_r1), point_add_bytes(nonces_r2)


def effective_nonce_x(agg_r1, agg_r2, aggpubkey_x: bytes, msg: bytes) -> bytes:
    """
    Compute the x-only final nonce ``R = aggR1 + b*aggR2``.

    :param agg_r1: aggregate first-round nonce point
    :param agg_r2: aggregate second-round nonce point
    :param aggpubkey_x: x-only aggregate public key used in the challenge
    :param msg: 32-byte message being signed
    :return: 32-byte x coordinate of the final nonce R
    """
    agg_r1_c = point_to_compressed(agg_r1)
    agg_r2_c = point_to_compressed(agg_r2)
    coeff = nonce_coeff(agg_r1_c + agg_r2_c, aggpubkey_x, msg)
    b_r2 = point_mul(agg_r2, coeff)
    final_r = point_add(agg_r1, b_r2)
    return xonly(point_to_compressed(final_r))


# ============================================================
# BIP340 Schnorr verification (host side, no card)
# ============================================================

def _lift_x_point(x_int: int):
    """Lift an x coordinate to the even-y curve point, or None if invalid."""
    if x_int >= P:
        return None
    y_sq = (pow(x_int, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None
    if y % 2 != 0:
        y = P - y
    return (x_int, y)


def schnorr_verify(pubkey_x: bytes, msg: bytes, signature: bytes) -> bool:
    """Verify a 64-byte BIP-340 Schnorr signature against an x-only public key."""
    if len(signature) != 64 or len(pubkey_x) != 32:
        return False

    point = _lift_x_point(int.from_bytes(pubkey_x, "big"))
    if point is None:
        return False

    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    if r >= P or s >= N:
        return False

    challenge = tagged_hash("BIP0340/challenge", signature[:32] + pubkey_x + msg)
    e = int.from_bytes(challenge, "big") % N

    # R = s*G - e*P
    s_g = point_mul(G, s)
    e_p = point_mul(point, e)
    neg_e_p = (e_p[0], (P - e_p[1]) % P)
    final_r = point_add(s_g, neg_e_p)

    if final_r[0] == 0 and final_r[1] == 0:
        return False
    if final_r[1] % 2 != 0:
        return False
    return final_r[0] == r


# ============================================================
# BIP341 Taproot
# ============================================================

def taproot_tweak(internal_key_xonly: bytes) -> int:
    """Return the Taproot tweak ``t`` for a key-path-only output."""
    digest = tagged_hash("TapTweak", internal_key_xonly)
    return int.from_bytes(digest, "big") % N


def taproot_output_key(internal_key_xonly: bytes):
    """
    Derive the Taproot output key from the x-only internal (aggregate) key.

    :return: tuple (Q_compressed, Q_xonly, tweak, q_has_even_y)
    """
    tweak = taproot_tweak(internal_key_xonly)
    internal_point = point_from_bytes(lift_x(internal_key_xonly))
    tweak_point = point_mul(G, tweak)
    output_point = point_add(internal_point, tweak_point)
    output_compressed = point_to_compressed(output_point)
    return output_compressed, xonly(output_compressed), tweak, has_even_y(output_compressed)


# ============================================================
# Bech32 / Bech32m (BIP173 / BIP350) for SegWit & Taproot addresses
# ============================================================

_BECH32M_CONST = 0x2bc830a3
_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values):
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp, data, const):
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0] * 6) ^ const
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret


def encode_segwit_address(witness_version: int, witness_program: bytes, hrp: str) -> str:
    """Encode a SegWit address (bech32 for v0, bech32m for v1+)."""
    const = 1 if witness_version == 0 else _BECH32M_CONST
    data = [witness_version] + _convertbits(list(witness_program), 8, 5)
    checksum = _bech32_create_checksum(hrp, data, const)
    return hrp + "1" + "".join(_CHARSET[d] for d in data + checksum)


def encode_taproot_address(witness_program: bytes, hrp: str) -> str:
    """Encode a Taproot (witness v1, bech32m) address."""
    return encode_segwit_address(1, witness_program, hrp)


def _bech32_data(addr: str, hrp: str):
    return [_CHARSET.index(c) for c in addr[len(hrp) + 1:]][:-6]


def decode_address_to_scriptpubkey(addr: str) -> bytes:
    """Convert a SegWit v0 (P2WPKH) or v1 (P2TR) address to its scriptPubKey."""
    lowered = addr.lower()
    for hrp in ("bc", "tb"):
        if lowered.startswith(hrp + "1q"):
            data = _bech32_data(addr, hrp)
            witness = bytes(_convertbits(data[1:], 5, 8, False))
            return b"\x00\x14" + witness
        if lowered.startswith(hrp + "1p"):
            data = _bech32_data(addr, hrp)
            witness = bytes(_convertbits(data[1:], 5, 8, False))
            return b"\x51\x20" + witness
    raise ValueError(f"Unsupported address: {addr}")


# ============================================================
# Transaction building (BIP341 key-path spend)
# ============================================================

def ser_compact_size(value: int) -> bytes:
    if value < 0xfd:
        return struct.pack("<B", value)
    if value <= 0xffff:
        return b"\xfd" + struct.pack("<H", value)
    if value <= 0xffffffff:
        return b"\xfe" + struct.pack("<I", value)
    return b"\xff" + struct.pack("<Q", value)


def ser_outpoint(txid_hex: str, vout: int) -> bytes:
    return bytes.fromhex(txid_hex)[::-1] + struct.pack("<I", vout)


def ser_output(value_sats: int, scriptpubkey: bytes) -> bytes:
    return struct.pack("<q", value_sats) + ser_compact_size(len(scriptpubkey)) + scriptpubkey


def compute_sighash_taproot(tx_version, tx_locktime, inputs, outputs, input_index,
                            amounts, scriptpubkeys) -> bytes:
    """Compute the BIP-341 key-path (SIGHASH_DEFAULT) sighash for one input."""
    prevouts = b"".join(ser_outpoint(txid, vout) for txid, vout, _ in inputs)
    hash_prevouts = hashlib.sha256(prevouts).digest()

    amounts_ser = b"".join(struct.pack("<q", amt) for amt in amounts)
    hash_amounts = hashlib.sha256(amounts_ser).digest()

    spks = b"".join(ser_compact_size(len(spk)) + spk for spk in scriptpubkeys)
    hash_scriptpubkeys = hashlib.sha256(spks).digest()

    sequences = b"".join(struct.pack("<I", seq) for _, _, seq in inputs)
    hash_sequences = hashlib.sha256(sequences).digest()

    outputs_ser = b"".join(ser_output(value, spk) for value, spk in outputs)
    hash_outputs = hashlib.sha256(outputs_ser).digest()

    preimage = b""
    preimage += b"\x00"                       # epoch
    preimage += b"\x00"                       # SIGHASH_DEFAULT
    preimage += struct.pack("<i", tx_version)
    preimage += struct.pack("<I", tx_locktime)
    preimage += hash_prevouts
    preimage += hash_amounts
    preimage += hash_scriptpubkeys
    preimage += hash_sequences
    preimage += hash_outputs
    preimage += b"\x00"                       # spend_type (key path)
    preimage += struct.pack("<I", input_index)

    return tagged_hash("TapSighash", preimage)


def build_signed_tx(tx_version, tx_locktime, inputs, outputs, signature) -> bytes:
    """Serialise a single-input Taproot key-path spend with the given witness signature."""
    tx = b""
    tx += struct.pack("<i", tx_version)
    tx += b"\x00\x01"                          # segwit marker + flag
    tx += ser_compact_size(len(inputs))
    for txid_hex, vout, seq in inputs:
        tx += ser_outpoint(txid_hex, vout)
        tx += b"\x00"                          # empty scriptSig
        tx += struct.pack("<I", seq)
    tx += ser_compact_size(len(outputs))
    for value, spk in outputs:
        tx += ser_output(value, spk)
    tx += b"\x01"                              # one witness element
    tx += ser_compact_size(len(signature))
    tx += signature
    tx += struct.pack("<I", tx_locktime)
    return tx
