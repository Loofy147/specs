"""
atomic_engines.py
------------------
Closes the gap between "checks['identity'] = True" (a supplied boolean) and
"IdentityValid = True" (a proved computation). Every function here takes real
evidence and returns (bool, transcript) -- the transcript is itself evidence,
inspectable and ledger-able, not just a pass/fail flag.

    IdentityValid(o)   := VerifyCertificate(cert)  AND CheckContinuity(chain)
                            AND VerifyLineage(lineage)
    Prov(q)             := signature over the provenance claim verifies
    Evid(q)              := SHA-256(evidence bytes) matches the committed hash
    Indep(q)             := 2 distinct, authorized, non-author verifier keys signed off
    SemEq(k, r)          := bounded exhaustive testing finds 0 disagreements between
                              candidate k and spec r over k's full finite input domain
    Adv(k)                := k survives a battery of adversarial/boundary inputs
    RuleCompat(q)          := q's declared constitution hash matches the ACTUAL
                                live hash of governance_math.tex on disk
"""

from __future__ import annotations

import hashlib
import itertools
from typing import Callable, Dict, List, Sequence, Tuple

import pki


Transcript = Dict[str, str]


# ---------------------------------------------------------------------------
# IdentityValid := VerifyCertificate AND CheckContinuity AND VerifyLineage
# ---------------------------------------------------------------------------

def identity_valid(
    cert: pki.Certificate,
    root_public_key,
    rotation_chain: List[pki.RotationRecord],
    current_public_key_bytes: bytes,
    lineage_chain: List[pki.LineageRecord],
) -> Tuple[bool, Transcript]:
    cert_ok, cert_reason = pki.verify_certificate(cert, root_public_key)
    cont_ok, cont_reason = pki.verify_continuity(
        cert.subject_public_key_bytes, rotation_chain, current_public_key_bytes
    )
    lin_ok, lin_reason = pki.verify_lineage(lineage_chain)
    transcript = {
        "VerifyCertificate": cert_reason,
        "CheckContinuity": cont_reason,
        "VerifyLineage": lin_reason,
    }
    return (cert_ok and cont_ok and lin_ok), transcript


# ---------------------------------------------------------------------------
# Prov(q) := provenance claim is signed by the claimed author's key
# ---------------------------------------------------------------------------

def prov_valid(author_public_key, claim_payload: bytes, claim_signature: bytes) -> Tuple[bool, str]:
    ok = pki.verify_signature(author_public_key, claim_payload, claim_signature)
    return ok, ("provenance signature verifies under author's key" if ok
                else "provenance signature does not verify -- claim is unauthenticated or forged")


# ---------------------------------------------------------------------------
# Evid(q) := evidence bytes hash to the committed digest
# ---------------------------------------------------------------------------

def evid_valid(evidence_bytes: bytes, committed_hash: str) -> Tuple[bool, str]:
    actual = hashlib.sha256(evidence_bytes).hexdigest()
    ok = actual == committed_hash
    return ok, (f"evidence matches commitment ({actual[:12]}...)" if ok
                else f"evidence hash mismatch: committed {committed_hash[:12]}..., actual {actual[:12]}... -- evidence was altered")


# ---------------------------------------------------------------------------
# Indep(q) := 2 distinct authorized verifiers, neither of which is the author
# ---------------------------------------------------------------------------

def indep_valid(verifier_a_fp: str, verifier_b_fp: str, author_fp: str,
                 authorized_verifiers: set) -> Tuple[bool, str]:
    if verifier_a_fp not in authorized_verifiers or verifier_b_fp not in authorized_verifiers:
        return False, "one or both verifiers are not in the authorized-verifier registry"
    if verifier_a_fp == verifier_b_fp:
        return False, "same verifier counted twice -- not independent"
    if author_fp in (verifier_a_fp, verifier_b_fp):
        return False, "a verifier is also the author -- conflict of interest"
    return True, f"two distinct authorized non-author verifiers ({verifier_a_fp}, {verifier_b_fp})"


# ---------------------------------------------------------------------------
# SemEq(k, r) := bounded exhaustive testing over k's real finite domain
# ---------------------------------------------------------------------------

def sem_eq_valid(candidate: Callable[[dict], bool], spec: Callable[[dict], bool],
                  var_names: Sequence[str]) -> Tuple[bool, str]:
    total = 0
    mismatches = 0
    first_cex = None
    for bits in itertools.product([False, True], repeat=len(var_names)):
        a = dict(zip(var_names, bits))
        total += 1
        if candidate(a) != spec(a):
            mismatches += 1
            if first_cex is None:
                first_cex = a
    ok = mismatches == 0
    detail = (f"exhaustively equivalent across all {total} assignments" if ok
              else f"{mismatches}/{total} disagreements, first at {first_cex}")
    return ok, detail


# ---------------------------------------------------------------------------
# Adv(k) := candidate survives a battery of adversarial / boundary cases
# ---------------------------------------------------------------------------

def adv_valid(candidate: Callable[..., object], cases: List[dict]) -> Tuple[bool, str]:
    failures = []
    for case in cases:
        try:
            result = candidate(*case["args"])
            if result != case["expected"]:
                failures.append(f"{case['label']}: got {result!r}, expected {case['expected']!r}")
        except Exception as e:
            failures.append(f"{case['label']}: raised {type(e).__name__}: {e}")
    ok = not failures
    detail = (f"survived all {len(cases)} adversarial cases" if ok
              else f"failed {len(failures)}/{len(cases)}: " + "; ".join(failures))
    return ok, detail


# ---------------------------------------------------------------------------
# RuleCompat(q) := declared constitution hash == the ACTUAL live hash on disk
# ---------------------------------------------------------------------------

def active_constitution_hash(tex_path: str = "/mnt/user-data/uploads/governance_math.tex") -> str:
    with open(tex_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def rule_compat_valid(declared_hash: str, tex_path: str = "/mnt/user-data/uploads/governance_math.tex") -> Tuple[bool, str]:
    active = active_constitution_hash(tex_path)
    ok = declared_hash == active
    return ok, (f"matches active constitution ({active[:12]}...)" if ok
                else f"declared {declared_hash[:12]}... != active {active[:12]}... -- implementation targets a stale/different constitution")
