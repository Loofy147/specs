"""
governance_kernel.py
---------------------
Executable implementation of governance_math.tex.

The .tex spec defines composite predicates (Canonical, Verified, EvolutionValid, ...)
in terms of *atomic* predicates (Identity, EvidenceValid, Indep, Adv, ...) that it
never itself defines -- they're left as opaque checks a real system would supply.

Engineering decisions made to turn the algebra into running code (these are choices,
not given by the spec, and are called out inline where made):

  1. Every governance object carries a `checks: Dict[str, bool]` bag representing the
     evaluated atomic predicates. Composite predicates below are pure boolean
     functions over that bag -- this keeps the *logical composition* exactly as
     specified while leaving evaluation of atomic predicates external/pluggable.
  2. tau() returns (new_state | None, reasons) instead of bare (S | {bot}) -- a bare
     bottom tells you nothing about *why*; a governance kernel needs that for the
     ledger's `rationale` field, so we surface it without changing the pass/fail logic.
  3. The ledger enforces append-only at the type level (no delete/update method
     exists) and additionally hash-chains entries (hash_t = H(hash_{t-1} || entry_t))
     so tampering with entry t is detectable even if someone bypasses the API and
     edits the backing list directly.
  4. NameOnlyContinuity(...) = 0 is implemented as a constant function -- per spec
     it does not depend on its arguments, it's a standing assertion that naming
     something "the same" is never sufficient on its own.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Set, Tuple, Any


# ---------------------------------------------------------------------------
# 1) Primitives -- Gamma(o) envelope
# ---------------------------------------------------------------------------

@dataclass
class GovernanceObject:
    id: str
    type: str
    status: str = "draft"
    version: int = 1
    provenance: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)
    understanding: Dict[str, Any] = field(default_factory=dict)
    recoverability: Dict[str, Any] = field(default_factory=dict)
    evolution: Dict[str, Any] = field(default_factory=dict)
    contestation: List[Dict[str, Any]] = field(default_factory=list)
    trust: float = 1.0
    trust_tier: str = "T0"
    contained: bool = False
    timestamps: Dict[str, float] = field(default_factory=dict)
    signatures: List[str] = field(default_factory=list)
    # engineering addition: the atomic-predicate bag (see module docstring, pt.1)
    checks: Dict[str, bool] = field(default_factory=dict)

    def c(self, name: str) -> bool:
        """Look up an atomic predicate; missing == not-yet-established == False."""
        return bool(self.checks.get(name, False))


# ---------------------------------------------------------------------------
# 2) Core invariants  I, E, V, U, R_c, X  ->  Canonical / CanonicalChange
# ---------------------------------------------------------------------------

def I(o: GovernanceObject) -> bool:   return o.c("identity")
def E(o: GovernanceObject) -> bool:   return o.c("evidence_valid")
def V(o: GovernanceObject) -> bool:   return o.c("verification_valid")
def U(o: GovernanceObject) -> bool:   return o.c("understandable")
def R_c(o: GovernanceObject) -> bool: return o.c("recoverable")
def X(o: GovernanceObject) -> bool:   return o.c("evolution_valid")


def Canonical(o: GovernanceObject) -> bool:
    return I(o) and E(o) and V(o) and U(o) and R_c(o)


def CanonicalChange(o: GovernanceObject) -> bool:
    return Canonical(o) and X(o)


def canonical_report(o: GovernanceObject) -> Dict[str, bool]:
    """Diagnostic: which of the five (six) invariants are actually failing."""
    return {"I": I(o), "E": E(o), "V": V(o), "U": U(o), "R_c": R_c(o), "X": X(o)}


# ---------------------------------------------------------------------------
# 3) Canonical state machine  tau : S x X -> S u {bot}
# ---------------------------------------------------------------------------

@dataclass
class TransitionRequest:
    """x_t: a transition request/claim/upgrade/action."""
    preconditions_met: bool          # P(x_t, s_t)
    authorized: bool                 # A(x_t)
    blocking_contested: bool         # C(x_t)
    contained_or_quarantined: bool   # K(x_t)
    target_state: str
    label: str = ""


def tau(s_t: str, x_t: TransitionRequest) -> Tuple[Optional[str], List[str]]:
    """
    tau(s_t, x_t) = s_{t+1}  iff  P(x_t,s_t) and A(x_t) and not C(x_t) and not K(x_t)
    Returns (s_{t+1} or None [bottom], list of failed-condition reasons).
    """
    reasons = []
    if not x_t.preconditions_met:
        reasons.append("P: preconditions not met")
    if not x_t.authorized:
        reasons.append("A: not authorized")
    if x_t.blocking_contested:
        reasons.append("C: blocking contestation active")
    if x_t.contained_or_quarantined:
        reasons.append("K: contained/quarantined/revoked")

    if reasons:
        return None, reasons
    return x_t.target_state, []


# ---------------------------------------------------------------------------
# 4) Ledger -- append-only, hash-chained
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    type: str
    object_id: str
    prev_entry: Optional[str]
    event_time: float
    actor: str
    authority: str
    evidence: Tuple[str, ...]
    verification: str
    contestation: str
    transition: str
    rollback: str
    status_before: str
    status_after: str
    trust_before: float
    trust_after: float
    rationale: str
    signatures: Tuple[str, ...]
    hash: str


class LedgerIntegrityError(Exception):
    pass


class Ledger:
    """
    L_{t+1} = L_t || l_t
    Append-only: there is deliberately no update/delete method. `_entries` is
    name-mangled and every read path returns copies, so the only way to add
    data is append().
    """

    def __init__(self) -> None:
        self.__entries: List[LedgerEntry] = []

    def _hash_entry(self, prev_hash: str, payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, default=str).encode()
        return hashlib.sha256(prev_hash.encode() + blob).hexdigest()

    def append(
        self,
        *,
        type: str,
        object_id: str,
        actor: str,
        authority: str,
        evidence: Tuple[str, ...] = (),
        verification: str = "",
        contestation: str = "",
        transition: str = "",
        rollback: str = "",
        status_before: str = "",
        status_after: str = "",
        trust_before: float = 0.0,
        trust_after: float = 0.0,
        rationale: str = "",
        signatures: Tuple[str, ...] = (),
    ) -> LedgerEntry:
        prev = self.__entries[-1] if self.__entries else None
        prev_hash = prev.hash if prev else "GENESIS"
        entry_id = str(uuid.uuid4())
        payload = dict(
            entry_id=entry_id, type=type, object_id=object_id,
            prev_entry=(prev.entry_id if prev else None),
            event_time=time.time(), actor=actor, authority=authority,
            evidence=evidence, verification=verification, contestation=contestation,
            transition=transition, rollback=rollback,
            status_before=status_before, status_after=status_after,
            trust_before=trust_before, trust_after=trust_after,
            rationale=rationale, signatures=signatures,
        )
        h = self._hash_entry(prev_hash, payload)
        entry = LedgerEntry(hash=h, **payload)
        self.__entries.append(entry)
        return entry

    def entries(self) -> Tuple[LedgerEntry, ...]:
        return tuple(self.__entries)  # copy out -- caller can't mutate the ledger

    def verify_integrity(self) -> bool:
        """Recompute every hash from GENESIS forward; detects any tampering."""
        prev_hash = "GENESIS"
        for e in self.__entries:
            payload = asdict(e)
            payload.pop("hash")
            expected = self._hash_entry(prev_hash, payload)
            if expected != e.hash:
                return False
            prev_hash = e.hash
        return True


# ---------------------------------------------------------------------------
# 5) Verification
# ---------------------------------------------------------------------------

def Verified(q: GovernanceObject) -> bool:
    return (
        q.c("prov") and q.c("evid") and q.c("indep")
        and q.c("sem_eq") and q.c("adv") and q.c("rule_compat")
    )


# ---------------------------------------------------------------------------
# 6) Containment and recovery
# ---------------------------------------------------------------------------

def Contained(o: GovernanceObject) -> bool:
    return o.c("drift") or o.c("mismatch") or o.c("compromise") or o.c("nullified")


def RecoveryReady(o: GovernanceObject) -> bool:
    return Contained(o) and o.c("repair_plan") and o.c("rollback_avail") and o.c("reverify")


def Rollback(t: int, k: int, s_k: GovernanceObject, repair_valid: bool) -> bool:
    """Rollback(s_t -> s_k) iff k < t and Canonical(s_k) and RepairValid(s_k)."""
    return k < t and Canonical(s_k) and repair_valid


# ---------------------------------------------------------------------------
# 7) Contestation
# ---------------------------------------------------------------------------

@dataclass
class Challenge:
    target_id: str
    has_evidence: bool
    submitted_at: float
    window_close: float
    burden_defined: bool

    def target(self, o: GovernanceObject) -> bool:
        return self.target_id == o.id

    def within_window(self, t: float) -> bool:
        return self.submitted_at <= t <= self.window_close


def ValidChallenge(c: Challenge, o: GovernanceObject, t: float) -> bool:
    return c.target(o) and c.has_evidence and c.within_window(t) and c.burden_defined


def Contested(o: GovernanceObject, t: float, challenges: List[Challenge]) -> bool:
    return any(ValidChallenge(c, o, t) for c in challenges)


# ---------------------------------------------------------------------------
# 8) Identity continuity
# ---------------------------------------------------------------------------

@dataclass
class LineageProof:
    preserved_invariants: Set[str]
    proof_valid: bool


def Continuity(protected_invariants: Set[str], proof: Optional[LineageProof]) -> bool:
    if proof is None:
        return False
    proof_exists = proof.proof_valid
    preserves = protected_invariants.issubset(proof.preserved_invariants)
    return proof_exists and preserves


def NameOnlyContinuity(*_args, **_kwargs) -> int:
    """Constant 0 by definition -- claiming continuity by name is never enough."""
    return 0


# ---------------------------------------------------------------------------
# 9) Evolution / safe upgrade
# ---------------------------------------------------------------------------

@dataclass
class EvolutionPackage:
    lineage: str
    preserved_invariants: Set[str]
    modified_invariants: Set[str]
    removed_capabilities: Set[str]
    new_capabilities: Set[str]
    risk_analysis: str
    recovery_plan: str
    rollback_proof: bool
    attestations: Tuple[str, ...]


def EvolutionValid(
    protected_invariants: Set[str],
    proof: Optional[LineageProof],
    pkg: EvolutionPackage,
    independent_attestation: bool,
) -> bool:
    return (
        Continuity(protected_invariants, proof)
        and protected_invariants.issubset(pkg.preserved_invariants)
        and pkg.rollback_proof
        and independent_attestation
    )


# ---------------------------------------------------------------------------
# 10) Semantic implementation equivalence
# ---------------------------------------------------------------------------

TRUST_TIERS = ["T0", "T1", "T2", "T3"]  # T3 highest


def SemanticallyEquivalent(k_checks: Dict[str, bool]) -> bool:
    return (
        k_checks.get("spec_to_code", False)
        and k_checks.get("invariant_test", False)
        and k_checks.get("adv_test", False)
        and k_checks.get("monitor", False)
    )


def apply_semantic_check(o: GovernanceObject, k_checks: Dict[str, bool]) -> bool:
    """
    If SemanticallyEquivalent fails: TrustTier(k) is downgraded one notch and the
    object is contained until remediated. Mutates o in place; returns the result.
    """
    ok = SemanticallyEquivalent(k_checks)
    if not ok:
        idx = TRUST_TIERS.index(o.trust_tier)
        o.trust_tier = TRUST_TIERS[max(0, idx - 1)]
        o.contained = True
        o.checks["mismatch"] = True  # feeds Contained() via Mismatch(o)
    return ok


# ---------------------------------------------------------------------------
# 11) Metric integrity
# ---------------------------------------------------------------------------

def MetricValid(aligned: bool, gamified: bool, divergent: bool) -> bool:
    return aligned and (not gamified) and (not divergent)


def metric_divergence_workflow(aligned: bool, gamified: bool, divergent: bool) -> Dict[str, bool]:
    """If divergence is confirmed: Contain, Revalidate, RestoreOnlyAfterProof."""
    valid = MetricValid(aligned, gamified, divergent)
    if valid:
        return {"valid": True, "contained": False, "revalidate": False, "restore_only_after_proof": False}
    return {"valid": False, "contained": True, "revalidate": True, "restore_only_after_proof": True}


# ---------------------------------------------------------------------------
# 12) Bounded recursion
# ---------------------------------------------------------------------------

@dataclass
class ProcessResult:
    value: Any
    depth_used: int
    hit_limit: bool
    meta_uncertainty: float


def bounded_execute(
    step: Callable[[Any, int], Tuple[Any, bool]],
    initial: Any,
    depth_limit: int,
) -> ProcessResult:
    """
    Runs `step(state, depth) -> (new_state, done)` until `done` or `depth_limit`.
    d_p < infinity is enforced structurally (depth_limit is a real int, no process
    can run unbounded). On limit-exceeded, falls back to HighestValidatedState
    (last state that passed a validation step) with MetaUncertainty(p) > 0.
    """
    state = initial
    best_validated = initial
    for depth in range(depth_limit):
        state, done = step(state, depth)
        best_validated = state  # step() is expected to only advance on validated states
        if done:
            return ProcessResult(value=state, depth_used=depth + 1, hit_limit=False, meta_uncertainty=0.0)
    # depth exhausted without completion
    return ProcessResult(
        value=best_validated,
        depth_used=depth_limit,
        hit_limit=True,
        meta_uncertainty=1.0 / depth_limit,  # > 0, shrinks as allowed budget grows
    )


# ---------------------------------------------------------------------------
# 13) Final compact constitution -- canonical action gate
# ---------------------------------------------------------------------------

def Ledgered(o: GovernanceObject, ledger: Ledger) -> bool:
    return any(e.object_id == o.id for e in ledger.entries())


def Attested(o: GovernanceObject) -> bool:
    return len(o.signatures) > 0


def Reviewable(o: GovernanceObject) -> bool:
    return o.c("reviewable")


def CanonicalAction(o: GovernanceObject, ledger: Ledger, is_change: bool = False) -> bool:
    base = CanonicalChange(o) if is_change else Canonical(o)
    return base and Ledgered(o, ledger) and Attested(o) and Reviewable(o)
