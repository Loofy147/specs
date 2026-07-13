"""
pki.py
------
A small, real public-key infrastructure used to derive IdentityValid(o) from
actual evidence instead of a stored boolean. Everything here is genuine Ed25519
signing/verification (via the `cryptography` package) and genuine SHA-256 hash
chaining -- nothing is simulated or mocked.

Three primitives, matching the three conjuncts the person asked for:

  VerifyCertificate  -> verify_certificate()   (root-signed identity certificate)
  CheckContinuity     -> verify_continuity()    (signed key-rotation hop chain)
  VerifyLineage        -> verify_lineage()       (hash-chained history, like the ledger)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, replace
from typing import List, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------

@dataclass
class KeyPair:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    def public_bytes(self) -> bytes:
        return self.public_key.public_bytes_raw()

    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_bytes()).hexdigest()[:16]

    def sign(self, payload: bytes) -> bytes:
        return self.private_key.sign(payload)


def generate_keypair() -> KeyPair:
    priv = Ed25519PrivateKey.generate()
    return KeyPair(private_key=priv, public_key=priv.public_key())


def verify_signature(public_key: Ed25519PublicKey, payload: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(signature, payload)
        return True
    except InvalidSignature:
        return False


def pubkey_from_bytes(b: bytes) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(b)


# ---------------------------------------------------------------------------
# Certificate  ("VerifyCertificate")
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Certificate:
    subject_id: str
    subject_public_key_bytes: bytes
    issued_at: float
    expires_at: float
    issuer_fingerprint: str
    signature: bytes = b""

    def payload(self) -> bytes:
        return json.dumps(
            dict(
                subject_id=self.subject_id,
                subject_public_key=self.subject_public_key_bytes.hex(),
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                issuer_fingerprint=self.issuer_fingerprint,
            ),
            sort_keys=True,
        ).encode()


def issue_certificate(root: KeyPair, subject_id: str, subject_public_key_bytes: bytes,
                       ttl_seconds: float = 3600 * 24 * 365) -> Certificate:
    now = time.time()
    unsigned = Certificate(subject_id, subject_public_key_bytes, now, now + ttl_seconds, root.fingerprint())
    return replace(unsigned, signature=root.sign(unsigned.payload()))


def verify_certificate(cert: Certificate, root_public_key: Ed25519PublicKey) -> Tuple[bool, str]:
    if time.time() > cert.expires_at:
        return False, "certificate expired"
    if verify_signature(root_public_key, cert.payload(), cert.signature):
        return True, "root signature valid, certificate current"
    return False, "root signature invalid (forged or corrupted certificate)"


# ---------------------------------------------------------------------------
# Key rotation continuity chain  ("CheckContinuity")
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RotationRecord:
    prior_public_key_bytes: bytes
    new_public_key_bytes: bytes
    signed_by_prior: bytes = b""

    def payload(self) -> bytes:
        return self.prior_public_key_bytes + self.new_public_key_bytes


def make_rotation(prior: KeyPair, new: KeyPair) -> RotationRecord:
    unsigned = RotationRecord(prior.public_bytes(), new.public_bytes())
    return replace(unsigned, signed_by_prior=prior.sign(unsigned.payload()))


def verify_continuity(genesis_public_key_bytes: bytes, chain: List[RotationRecord],
                       current_public_key_bytes: bytes) -> Tuple[bool, str]:
    if not chain:
        ok = genesis_public_key_bytes == current_public_key_bytes
        return ok, ("genesis key is still the current key (no rotation)" if ok
                     else "no rotation on record but genesis key != claimed current key")

    expected_prior = genesis_public_key_bytes
    for i, rec in enumerate(chain):
        if rec.prior_public_key_bytes != expected_prior:
            return False, f"hop {i}: chain link broken -- prior key in this record doesn't match the previous hop's new key"
        prior_pub = pubkey_from_bytes(rec.prior_public_key_bytes)
        if not verify_signature(prior_pub, rec.payload(), rec.signed_by_prior):
            return False, f"hop {i}: signature invalid -- this handoff was not authorized by the actual prior key"
        expected_prior = rec.new_public_key_bytes

    if expected_prior != current_public_key_bytes:
        return False, "rotation chain complete but does not terminate at the claimed current key"
    return True, f"continuity verified across {len(chain)} signed hop(s)"


# ---------------------------------------------------------------------------
# Lineage  ("VerifyLineage") -- hash-chained history, same pattern as Ledger
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LineageRecord:
    event: str
    detail: str
    prev_hash: str
    hash: str = ""


def _lineage_hash(prev_hash: str, event: str, detail: str) -> str:
    return hashlib.sha256((prev_hash + "|" + event + "|" + detail).encode()).hexdigest()


def build_lineage(events: List[Tuple[str, str]]) -> List[LineageRecord]:
    chain: List[LineageRecord] = []
    prev = "GENESIS"
    for event, detail in events:
        h = _lineage_hash(prev, event, detail)
        chain.append(LineageRecord(event, detail, prev, h))
        prev = h
    return chain


def verify_lineage(chain: List[LineageRecord]) -> Tuple[bool, str]:
    prev = "GENESIS"
    for i, rec in enumerate(chain):
        if rec.prev_hash != prev:
            return False, f"entry {i}: prev_hash pointer broken"
        expected = _lineage_hash(prev, rec.event, rec.detail)
        if expected != rec.hash:
            return False, f"entry {i}: hash mismatch -- record tampered after the fact"
        prev = rec.hash
    n = len(chain)
    return True, f"lineage verified across {n} entr{'y' if n == 1 else 'ies'}"
