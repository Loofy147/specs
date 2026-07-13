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
# Summary
# ---------------------------------------------------------------------------

hr("Summary")
print("1) Cross-check vs. exhaustive result :", "MATCH (both proved it)" if s.check() == z3.unsat else "MISMATCH -- investigate")
print("2) Alignment composition (real)      :", "PROVEN" if result2 == z3.unsat else "NOT proven")
print("3) Tightened bound (expected false)  :", "correctly REFUTED with a witness" if result3 == z3.sat else "unexpectedly not refuted")
print("4) Trust-decay clamp monotonicity    :", "PROVEN" if result4 == z3.unsat else "NOT proven")
