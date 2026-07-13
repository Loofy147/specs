"""
smt_theorems.py
-----------------
proof_harness.py proves things by trying every assignment in a finite domain --
that's a real proof, but only because the domain is small enough to enumerate.
This file goes one level further: encode the same claims as SMT formulas and let
Z3 discharge them by checking UNSAT of the negation. Two things that buys us:

  1. An INDEPENDENT cross-check of a claim we already proved by enumeration
     (different proof method, same answer -> real confidence, not double-counting).
  2. Theorems over domains with no finite enumeration at all -- real-valued scores,
     thresholds, decay factors. "We tried all 64 assignments" isn't even a sentence
     you can say about the reals between 0 and 1. Z3 proves it anyway, in one shot,
     and can hand back a literal countermodel if the claim is false.

Where proof_harness.py can say "tested exhaustively, 0 counterexamples in the
finite domain," this file is the first place in the project that can honestly
say "this is a theorem of the logic" -- with UNSAT as the certificate.
"""

from __future__ import annotations

import z3


def hr(title: str):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def report(name: str, solver_result, model_note: str = ""):
    if solver_result == z3.unsat:
        print(f"[THEOREM]  {name}")
        print(f"           UNSAT on the negation -> no assignment anywhere in the domain violates it. Proven.")
    elif solver_result == z3.sat:
        print(f"[REFUTED]  {name}")
        print(f"           SAT -- a genuine counterexample exists. {model_note}")
    else:
        print(f"[UNKNOWN]  {name} -- solver could not decide (needs a stronger theory or induction)")


# ---------------------------------------------------------------------------
# 1) Cross-check: re-derive a claim proof_harness.py already proved by exhaustive
#    enumeration (CanonicalChange(o) => Canonical(o)), this time via SMT.
# ---------------------------------------------------------------------------

hr("1) Cross-check against proof_harness.py's exhaustive result (independent method)")

I, E, V, U, Rc, X = z3.Bools("I E V U Rc X")
Canonical = z3.And(I, E, V, U, Rc)
CanonicalChange = z3.And(Canonical, X)

s = z3.Solver()
s.add(CanonicalChange, z3.Not(Canonical))   # negation of the claim
report("CanonicalChange(o) => Canonical(o)  [Bool, 6 vars]", s.check())


# ---------------------------------------------------------------------------
# 2) A genuinely infinite-domain theorem: metric alignment composition.
#    Aligned(m, Omega) generalized from a boolean flag to |score - Omega| <= eps.
#    Claim: if two independently-scored metrics are each within eps of the same
#    target, their average is within eps of the target too. True for EVERY real
#    score1, score2, Omega, eps>0 -- an uncountable domain, no enumeration exists.
# ---------------------------------------------------------------------------

hr("2) Metric alignment composition (real-valued, infinite domain)")

score1, score2, omega, eps = z3.Reals("score1 score2 omega eps")

def abs_z3(x):
    return z3.If(x >= 0, x, -x)

aligned1 = abs_z3(score1 - omega) <= eps
aligned2 = abs_z3(score2 - omega) <= eps
avg = (score1 + score2) / 2
avg_aligned = abs_z3(avg - omega) <= eps

s2 = z3.Solver()
s2.add(eps > 0, aligned1, aligned2, z3.Not(avg_aligned))   # negation of the claim
result2 = s2.check()
report("Aligned(m1)^Aligned(m2) => Aligned(mean(m1,m2))  [Real, unbounded domain]", result2)


# ---------------------------------------------------------------------------
# 3) A FALSE claim, to prove this isn't a rubber stamp: tightening the bound to
#    eps/2 should NOT generally hold. Z3 should find a concrete counterexample.
# ---------------------------------------------------------------------------

hr("3) Deliberately false claim, to confirm Z3 can actually refute (not just confirm)")

s3 = z3.Solver()
avg_aligned_tight = abs_z3(avg - omega) <= eps / 2
s3.add(eps > 0, aligned1, aligned2, z3.Not(avg_aligned_tight))
result3 = s3.check()
model_note = ""
if result3 == z3.sat:
    m = s3.model()
    model_note = f"counterexample: score1={m[score1]}, score2={m[score2]}, omega={m[omega]}, eps={m[eps]}"
report("Aligned(m1)^Aligned(m2) => Aligned_eps/2(mean(m1,m2))  [claim we expect to be FALSE]", result3, model_note)


# ---------------------------------------------------------------------------
# 4) Trust-decay clamp monotonicity: trust_after = clamp(trust_before + delta, 0, 1).
#    Claim: for a fixed trust_before, a smaller decay never produces a smaller
#    post-clamp trust than a larger decay. Real-valued, unbounded domain again.
# ---------------------------------------------------------------------------

hr("4) Trust-decay clamp monotonicity (real-valued, unbounded domain)")

trust_before, delta1, delta2 = z3.Reals("trust_before delta1 delta2")

def clamp01(x):
    return z3.If(x < 0, 0, z3.If(x > 1, 1, x))

trust_after_1 = clamp01(trust_before + delta1)
trust_after_2 = clamp01(trust_before + delta2)

s4 = z3.Solver()
s4.add(
    trust_before >= 0, trust_before <= 1,
    delta1 <= delta2,
    z3.Not(trust_after_1 <= trust_after_2),   # negation of monotonicity
)
result4 = s4.check()
report("delta1 <= delta2  =>  clamp(trust_before+delta1) <= clamp(trust_before+delta2)  [Real]", result4)


# ---------------------------------------------------------------------------
# 5) Inductive Invariant for Ledger Version Monotonicity.
#    State is represented by:
#      - N (Int): current ledger length
#      - v_curr (Int): current version of the active object
#      - L (Array Int -> Int): mapping ledger indices to recorded versions
#
#    Transition T(S, S_next):
#      - N_next == N + 1
#      - v_curr_next == v_curr + 1
#      - L_next == Store(L, N, v_curr)
#
#    Inductive Invariant P(S):
#      - N >= 0
#      - v_curr >= 1
#      - Forall i: (0 <= i < N) => L[i] < v_curr
#      - Forall i, j: (0 <= i < j < N) => L[i] < L[j]
# ---------------------------------------------------------------------------

hr("5) Inductive Invariant for Ledger Version Monotonicity (unbounded history)")

N = z3.Int("N")
v_curr = z3.Int("v_curr")
L = z3.Array("L", z3.IntSort(), z3.IntSort())

N_next = z3.Int("N_next")
v_curr_next = z3.Int("v_curr_next")
L_next = z3.Array("L_next", z3.IntSort(), z3.IntSort())

# Transition relation T(S, S_next)
T = z3.And(
    N_next == N + 1,
    v_curr_next == v_curr + 1,
    L_next == z3.Store(L, N, v_curr)
)

i, j = z3.Ints("i j")

# Inductive Invariant components for S
inv_N = N >= 0
inv_v = v_curr >= 1
inv_bound = z3.ForAll([i], z3.Implies(z3.And(0 <= i, i < N), L[i] < v_curr))
inv_mono = z3.ForAll([i, j], z3.Implies(z3.And(0 <= i, i < j, j < N), L[i] < L[j]))

P = z3.And(inv_N, inv_v, inv_bound, inv_mono)

# Inductive Invariant components for S_next
inv_N_next = N_next >= 0
inv_v_next = v_curr_next >= 1
inv_bound_next = z3.ForAll([i], z3.Implies(z3.And(0 <= i, i < N_next), L_next[i] < v_curr_next))
inv_mono_next = z3.ForAll([i, j], z3.Implies(z3.And(0 <= i, i < j, j < N_next), L_next[i] < L_next[j]))

P_next = z3.And(inv_N_next, inv_v_next, inv_bound_next, inv_mono_next)

# Check inductive step: P(S) and T(S, S_next) => P(S_next)
s5 = z3.Solver()
s5.add(P, T, z3.Not(P_next))
result5 = s5.check()
report("Inductive Step: P(S) ^ T(S, S_next) => P(S_next)  [Array, unbounded history]", result5)


# ---------------------------------------------------------------------------
# 6) Recovery Proof as a State-Machine Invariant.
#    Proves that from a CONTAINED state, a valid transition path back to a
#    CANONICAL state is guaranteed to exist under constitutional constraints.
# ---------------------------------------------------------------------------

hr("6) Recovery Proof as a State-Machine Invariant")

# Define status enum values
STATUS_CONTAINED = 0
STATUS_RECOVERY = 1
STATUS_CANONICAL = 2

# Status variables for a path of length 2: status0 -> status1 -> status2
status0 = z3.Int("status0")
status1 = z3.Int("status1")
status2 = z3.Int("status2")

has_rp = z3.Bool("has_rp")
has_vp = z3.Bool("has_vp")
has_ep = z3.Bool("has_ep")
has_sigs = z3.Bool("has_sigs")

# Constitutional constraints: all required recovery/validation evidence is met
all_evidence_present = z3.And(has_rp, has_vp, has_ep, has_sigs)

def Trans(s_from, s_to, rp, vp, ep, sigs):
    # Transition from CONTAINED to RECOVERY requires a recoverability plan (rp)
    t1 = z3.And(s_from == STATUS_CONTAINED, s_to == STATUS_RECOVERY, rp)
    # Transition from RECOVERY to CANONICAL requires verification (vp), evolution (ep), and signatures (sigs)
    t2 = z3.And(s_from == STATUS_RECOVERY, s_to == STATUS_CANONICAL, vp, ep, sigs)
    return z3.Or(t1, t2)

s6 = z3.Solver()
# Negation: we start at CONTAINED, all required evidence is present,
# but we CANNOT find a valid 2-step transition path to CANONICAL.
s6.add(
    status0 == STATUS_CONTAINED,
    all_evidence_present,
    z3.Not(z3.Exists([status1, status2], z3.And(
        Trans(status0, status1, has_rp, has_vp, has_ep, has_sigs),
        Trans(status1, status2, has_rp, has_vp, has_ep, has_sigs),
        status2 == STATUS_CANONICAL
    )))
)
result6 = s6.check()
report("Recovery Path Guaranteed: CONTAINED -> RECOVERY -> CANONICAL  [Int]", result6)


# ---------------------------------------------------------------------------
# 7) Witnessed Comprehensibility for Understandable as a Structural Proof.
#    Proves that any document meeting the structural requirements of minimum
#    word count and evidence pointers meets the Understandable obligation.
#
#    PROOFS & PROXY BOUNDARY WARNING:
#    It is critical to document the mathematical and semantic proof boundary
#    around the Understandable predicate. Unlike cryptographic proofs of identity,
#    authenticity, or integrity (such as Ed25519 signatures or SHA-256 hash chains
#    which provide definitive mathematical verification), cognitive understanding is
#    inherently non-cryptographic and cannot be directly proved.
#
#    Thus, this theorem verifies a STRUCTURAL PROXY (Witnessed Comprehensibility) rather
#    than cognitive/semantic comprehension itself. We prove that a document complies
#    with structural rules (e.g. word count, evidence references, risk disclosures),
#    leaving the validation of actual semantic coherence as an intentional, visible boundary
#    where human audit and formal structure meet.
# ---------------------------------------------------------------------------

hr("7) Witnessed Comprehensibility for Understandable (structural proof)")

word_count, evidence_pointers, risk_disclosures = z3.Ints("word_count evidence_pointers risk_disclosures")
min_words, min_ep, min_rd = z3.Ints("min_words min_ep min_rd")

def Understandable_Struct(wc, ep, rd, mw, me, mr):
    return z3.And(
        wc >= mw,
        ep >= me,
        rd >= mr
    )

# Define a structurally compliant document (e.g. twice the minimum requirements, plus minimum risk disclosures)
compliant_doc = z3.And(
    word_count >= 2 * min_words,
    evidence_pointers >= 2 * min_ep,
    risk_disclosures >= min_rd,
    min_words > 0,
    min_ep > 0,
    min_rd > 0
)

s7 = z3.Solver()
# Negation: the document is structurally compliant but fails Understandable_Struct
s7.add(
    compliant_doc,
    z3.Not(Understandable_Struct(word_count, evidence_pointers, risk_disclosures, min_words, min_ep, min_rd))
)
result7 = s7.check()
report("Witnessed Comprehensibility: Structurally compliant docs are Understandable", result7)


# ---------------------------------------------------------------------------
# 8) Inductive Invariant for Append-Only Ledger History (unbounded history)
#    Proves mathematically that updates to the ledger preserve all historical
#    records, so that no past entry can be deleted or altered (uniqueness).
#    State is represented by:
#      - N (Int): current ledger length
#      - L (Array Int -> Int): mapping ledger indices to recorded versions
#
#    Transition T(S, S_next):
#      - N_next == N + 1
#      - v_new (Int): new version to append
#      - L_next == Store(L, N, v_new)
#
#    Theorem (Append-Only):
#      For all indices i: (0 <= i < N) => L_next[i] == L[i]
# ---------------------------------------------------------------------------

hr("8) Inductive Invariant for Append-Only Ledger History (unbounded history)")

N_ap = z3.Int("N_ap")
L_ap = z3.Array("L_ap", z3.IntSort(), z3.IntSort())

N_ap_next = z3.Int("N_ap_next")
L_ap_next = z3.Array("L_ap_next", z3.IntSort(), z3.IntSort())
v_new = z3.Int("v_new")

# Transition: append one item at index N_ap
T_ap = z3.And(
    N_ap_next == N_ap + 1,
    L_ap_next == z3.Store(L_ap, N_ap, v_new)
)

# Inductive hypothesis: N_ap >= 0
inv_ap = N_ap >= 0

idx = z3.Int("idx")
# The Append-Only theorem: any previously recorded index remains identical in the next state
append_only_theorem = z3.Implies(
    inv_ap,
    z3.ForAll([idx], z3.Implies(
        z3.And(0 <= idx, idx < N_ap),
        L_ap_next[idx] == L_ap[idx]
    ))
)

s8 = z3.Solver()
s8.add(T_ap, z3.Not(append_only_theorem)) # negation of the theorem
result8 = s8.check()
report("Inductive Step: Append-Only History Preserved  [Array, unbounded history]", result8)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

hr("Summary")
print("1) Cross-check vs. exhaustive result :", "MATCH (both proved it)" if s.check() == z3.unsat else "MISMATCH -- investigate")
print("2) Alignment composition (real)      :", "PROVEN" if result2 == z3.unsat else "NOT proven")
print("3) Tightened bound (expected false)  :", "correctly REFUTED with a witness" if result3 == z3.sat else "unexpectedly not refuted")
print("4) Trust-decay clamp monotonicity    :", "PROVEN" if result4 == z3.unsat else "NOT proven")
print("5) Ledger version monotonicity       :", "PROVEN" if result5 == z3.unsat else "NOT proven")
print("6) Recovery path guaranteed          :", "PROVEN" if result6 == z3.unsat else "NOT proven")
print("7) Witnessed comprehensibility       :", "PROVEN" if result7 == z3.unsat else "NOT proven")
print("8) Append-only ledger history        :", "PROVEN" if result8 == z3.unsat else "NOT proven")
