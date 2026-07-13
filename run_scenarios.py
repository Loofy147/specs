"""
run_scenarios.py
-----------------
Exercises kernel.py against constructed cases and asserts the boolean algebra
in governance_math.tex actually behaves the way the spec claims once it's real
code. Each scenario is a small, focused empirical check -- not just "it runs."
"""

import time
from kernel import (
    GovernanceObject, TransitionRequest, tau,
    Canonical, CanonicalChange, canonical_report,
    Ledger, LedgerIntegrityError,
    Verified,
    Contained, RecoveryReady, Rollback,
    Challenge, ValidChallenge, Contested,
    LineageProof, Continuity, NameOnlyContinuity,
    EvolutionPackage, EvolutionValid,
    SemanticallyEquivalent, apply_semantic_check,
    MetricValid, metric_divergence_workflow,
    bounded_execute, ProcessResult,
    Ledgered, Attested, Reviewable, CanonicalAction,
)

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def make_object(id_="o1", **overrides) -> GovernanceObject:
    checks = dict(
        identity=True, evidence_valid=True, verification_valid=True,
        understandable=True, recoverable=True, evolution_valid=True,
    )
    checks.update(overrides.pop("checks", {}))
    o = GovernanceObject(id=id_, type="policy", checks=checks, **overrides)
    return o


print("=" * 70)
print("1) Canonical / CanonicalChange -- full pass and single-invariant break")
print("=" * 70)

o_full = make_object("policy-001")
check("fully-satisfied object is Canonical", Canonical(o_full))
check("fully-satisfied object is CanonicalChange", CanonicalChange(o_full))

o_broken = make_object("policy-002", checks={"recoverable": False})
report = canonical_report(o_broken)
check(
    "breaking only R_c makes Canonical False, others still True",
    (not Canonical(o_broken)) and report["I"] and report["E"] and report["V"] and report["U"],
    detail=str(report),
)

o_change_broken = make_object("policy-003", checks={"evolution_valid": False})
check(
    "Canonical True but X False => Canonical True, CanonicalChange False",
    Canonical(o_change_broken) and (not CanonicalChange(o_change_broken)),
)


print()
print("=" * 70)
print("2) State machine tau -- each of P, A, C, K independently blocks")
print("=" * 70)

happy = TransitionRequest(True, True, False, False, target_state="active", label="happy")
s_next, reasons = tau("draft", happy)
check("all four conditions true => transition succeeds", s_next == "active" and reasons == [])

for label, kwargs in [
    ("P false blocks", dict(preconditions_met=False, authorized=True, blocking_contested=False, contained_or_quarantined=False)),
    ("A false blocks", dict(preconditions_met=True, authorized=False, blocking_contested=False, contained_or_quarantined=False)),
    ("C true blocks",  dict(preconditions_met=True, authorized=True, blocking_contested=True, contained_or_quarantined=False)),
    ("K true blocks",  dict(preconditions_met=True, authorized=True, blocking_contested=False, contained_or_quarantined=True)),
]:
    req = TransitionRequest(target_state="active", **kwargs)
    s_next, reasons = tau("draft", req)
    check(f"tau: {label}", s_next is None and len(reasons) == 1, detail=str(reasons))


print()
print("=" * 70)
print("3) Ledger -- append-only, hash-chained, tamper-evident")
print("=" * 70)

ledger = Ledger()
e1 = ledger.append(type="create", object_id="policy-001", actor="woohan",
                    authority="root", status_after="draft", trust_after=1.0,
                    rationale="initial creation")
e2 = ledger.append(type="transition", object_id="policy-001", actor="woohan",
                    authority="root", status_before="draft", status_after="active",
                    trust_before=1.0, trust_after=1.0, transition="draft->active",
                    rationale="published")

check("ledger has 2 entries in append order", [e.type for e in ledger.entries()] == ["create", "transition"])
check("second entry links to first via prev_entry", ledger.entries()[1].prev_entry == e1.entry_id)
check("ledger has no public mutate/delete method",
      not hasattr(Ledger, "delete") and not hasattr(Ledger, "update") and not hasattr(Ledger, "overwrite"))
check("hash chain verifies clean", ledger.verify_integrity())

# tamper: reach past the API into the name-mangled backing list and edit an entry
import dataclasses
tampered_entries = list(ledger._Ledger__entries)
tampered_entries[0] = dataclasses.replace(tampered_entries[0], rationale="ALTERED AFTER THE FACT")
ledger._Ledger__entries[0] = tampered_entries[0]
check("tampering an entry breaks hash-chain verification", not ledger.verify_integrity())


print()
print("=" * 70)
print("4) Verified(q) -- all six sub-checks required")
print("=" * 70)

q_ok = make_object("claim-001", checks=dict(
    identity=True, evidence_valid=True, verification_valid=True, understandable=True,
    recoverable=True, evolution_valid=True,
    prov=True, evid=True, indep=True, sem_eq=True, adv=True, rule_compat=True,
))
check("all six verification sub-checks true => Verified", Verified(q_ok))

q_bad = make_object("claim-002", checks=dict(prov=True, evid=True, indep=False,
                                              sem_eq=True, adv=True, rule_compat=True))
check("independence failing alone breaks Verified", not Verified(q_bad))


print()
print("=" * 70)
print("5) Containment / recovery / rollback")
print("=" * 70)

o_drift = make_object("policy-004", checks={"drift": True})
check("drift alone triggers Contained", Contained(o_drift))

o_clean = make_object("policy-005")
check("no drift/mismatch/compromise/nullified => not Contained", not Contained(o_clean))

o_recover = make_object("policy-006", checks={
    "drift": True, "repair_plan": True, "rollback_avail": True, "reverify": True,
})
check("contained + all recovery pieces => RecoveryReady", RecoveryReady(o_recover))

o_partial_recover = make_object("policy-007", checks={"drift": True, "repair_plan": True})
check("contained but missing rollback_avail/reverify => not RecoveryReady",
      not RecoveryReady(o_partial_recover))

s_target = make_object("policy-008-snapshot")  # fully canonical by default
check("valid rollback: k<t and target canonical and repair valid",
      Rollback(t=5, k=2, s_k=s_target, repair_valid=True))
check("invalid rollback: k>=t rejected even if target canonical",
      not Rollback(t=2, k=2, s_k=s_target, repair_valid=True))
non_canon_target = make_object("policy-009-snapshot", checks={"identity": False})
check("invalid rollback: target snapshot not canonical rejected",
      not Rollback(t=5, k=2, s_k=non_canon_target, repair_valid=True))


print()
print("=" * 70)
print("6) Contestation -- window and evidence gating")
print("=" * 70)

o_target = make_object("policy-010")
now = 1000.0
c_valid = Challenge(target_id="policy-010", has_evidence=True, submitted_at=990, window_close=1010, burden_defined=True)
c_expired = Challenge(target_id="policy-010", has_evidence=True, submitted_at=900, window_close=950, burden_defined=True)
c_no_evidence = Challenge(target_id="policy-010", has_evidence=False, submitted_at=990, window_close=1010, burden_defined=True)
c_wrong_target = Challenge(target_id="other-object", has_evidence=True, submitted_at=990, window_close=1010, burden_defined=True)

check("in-window, evidenced challenge is valid", ValidChallenge(c_valid, o_target, now))
check("expired-window challenge is invalid", not ValidChallenge(c_expired, o_target, now))
check("evidence-free challenge is invalid", not ValidChallenge(c_no_evidence, o_target, now))
check("wrong-target challenge is invalid", not ValidChallenge(c_wrong_target, o_target, now))
check("object is Contested if >=1 valid challenge exists among many invalid ones",
      Contested(o_target, now, [c_expired, c_no_evidence, c_wrong_target, c_valid]))
check("object is not Contested if zero valid challenges exist",
      not Contested(o_target, now, [c_expired, c_no_evidence, c_wrong_target]))


print()
print("=" * 70)
print("7) Continuity -- proof-carrying, never name-only")
print("=" * 70)

protected = {"identity", "trust_ledger", "governance_root"}
good_proof = LineageProof(preserved_invariants={"identity", "trust_ledger", "governance_root", "extra"}, proof_valid=True)
partial_proof = LineageProof(preserved_invariants={"identity", "trust_ledger"}, proof_valid=True)  # missing governance_root
invalid_proof = LineageProof(preserved_invariants=protected, proof_valid=False)

check("proof covering all protected invariants => Continuity holds", Continuity(protected, good_proof))
check("proof missing one protected invariant => Continuity fails", not Continuity(protected, partial_proof))
check("structurally-complete but proof_valid=False => Continuity fails", not Continuity(protected, invalid_proof))
check("no proof at all => Continuity fails", not Continuity(protected, None))
check("NameOnlyContinuity is always 0, regardless of args", NameOnlyContinuity("s7", "s8", claim="we are the same") == 0)


print()
print("=" * 70)
print("8) EvolutionValid -- four independent gates")
print("=" * 70)

pkg_ok = EvolutionPackage(
    lineage="policy-001 v1 -> v2", preserved_invariants={"identity", "trust_ledger", "governance_root"},
    modified_invariants=set(), removed_capabilities=set(), new_capabilities={"batch_mode"},
    risk_analysis="low", recovery_plan="rollback to v1 snapshot",
    rollback_proof=True, attestations=("verifier-a", "verifier-b"),
)
check("continuity + preserves + rollback_proof + attestation => EvolutionValid",
      EvolutionValid(protected, good_proof, pkg_ok, independent_attestation=True))

pkg_no_rollback = EvolutionPackage(
    lineage="policy-001 v1 -> v2", preserved_invariants={"identity", "trust_ledger", "governance_root"},
    modified_invariants=set(), removed_capabilities=set(), new_capabilities=set(),
    risk_analysis="low", recovery_plan="none", rollback_proof=False,
    attestations=("verifier-a",),
)
check("missing rollback_proof alone invalidates evolution even with good continuity",
      not EvolutionValid(protected, good_proof, pkg_no_rollback, independent_attestation=True))

check("missing independent attestation alone invalidates evolution",
      not EvolutionValid(protected, good_proof, pkg_ok, independent_attestation=False))


print()
print("=" * 70)
print("9) SemanticallyEquivalent -- failure downgrades trust + contains")
print("=" * 70)

impl_object = make_object("impl-001")
impl_object.trust_tier = "T2"
ok = apply_semantic_check(impl_object, dict(spec_to_code=True, invariant_test=True, adv_test=True, monitor=True))
check("all four sub-checks true => SemanticallyEquivalent, no side effects",
      ok and impl_object.trust_tier == "T2" and not impl_object.contained)

impl_object2 = make_object("impl-002")
impl_object2.trust_tier = "T2"
ok2 = apply_semantic_check(impl_object2, dict(spec_to_code=True, invariant_test=False, adv_test=True, monitor=True))
check("invariant_test failing => not equivalent, trust downgraded one tier, object contained",
      (not ok2) and impl_object2.trust_tier == "T1" and impl_object2.contained and Contained(impl_object2),
      detail=f"trust_tier={impl_object2.trust_tier}")


print()
print("=" * 70)
print("10) Metric integrity -- divergence workflow")
print("=" * 70)

check("aligned, not gamified, not divergent => MetricValid True", MetricValid(True, False, False))
wf = metric_divergence_workflow(aligned=True, gamified=True, divergent=False)
check("gamed metric triggers Contain+Revalidate+RestoreOnlyAfterProof",
      wf == {"valid": False, "contained": True, "revalidate": True, "restore_only_after_proof": True},
      detail=str(wf))


print()
print("=" * 70)
print("11) Bounded recursion -- completes within budget, and falls back when it doesn't")
print("=" * 70)

def converging_step(state, depth):
    # toy fixed-point search: halve the gap to a target each step
    target = 10.0
    new_state = state + (target - state) * 0.6
    done = abs(target - new_state) < 0.01
    return new_state, done

res_ok = bounded_execute(converging_step, initial=0.0, depth_limit=50)
check("process converges within depth budget => hit_limit False, meta_uncertainty 0",
      (not res_ok.hit_limit) and res_ok.meta_uncertainty == 0.0,
      detail=f"depth_used={res_ok.depth_used}, value={res_ok.value:.4f}")

def never_converges(state, depth):
    return state + 0.0001, False  # deliberately too slow to finish

res_bad = bounded_execute(never_converges, initial=0.0, depth_limit=20)
check("process exceeding depth budget => hit_limit True, meta_uncertainty > 0, d_p stayed finite",
      res_bad.hit_limit and res_bad.meta_uncertainty > 0.0 and res_bad.depth_used == 20,
      detail=f"meta_uncertainty={res_bad.meta_uncertainty:.4f}")


print()
print("=" * 70)
print("12) Final compact constitution -- CanonicalAction gate")
print("=" * 70)

final_ledger = Ledger()
o_final = make_object("policy-100")
final_ledger.append(type="create", object_id="policy-100", actor="woohan", authority="root")
o_final.signatures = ["sig-woohan"]
o_final.checks["reviewable"] = True
check("canonical + ledgered + attested + reviewable => CanonicalAction True",
      CanonicalAction(o_final, final_ledger, is_change=False))

o_final_unsigned = make_object("policy-101")
final_ledger.append(type="create", object_id="policy-101", actor="woohan", authority="root")
o_final_unsigned.checks["reviewable"] = True
check("canonical + ledgered + reviewable but NOT attested => CanonicalAction False",
      not CanonicalAction(o_final_unsigned, final_ledger, is_change=False))

o_not_ledgered = make_object("policy-102")
o_not_ledgered.signatures = ["sig-woohan"]
o_not_ledgered.checks["reviewable"] = True
check("canonical + attested + reviewable but NOT ledgered => CanonicalAction False",
      not CanonicalAction(o_not_ledgered, final_ledger, is_change=False))


print()
print("=" * 70)
print("13) Edge cases / adversarial stress")
print("=" * 70)

check("repair_valid=False blocks rollback even with k<t and canonical target",
      not Rollback(t=5, k=2, s_k=s_target, repair_valid=False))

o_x_only = make_object("policy-200", checks={"identity": False})  # I false, X true
check("X true alone cannot make CanonicalChange true if base Canonical is false",
      (not Canonical(o_x_only)) and (not CanonicalChange(o_x_only)))

# Check strict schema validation on construction
try:
    make_object("policy-invalid-checks", checks={"misspelled_key": True})
    strict_schema_validation_passed = False
except KeyError:
    strict_schema_validation_passed = True
check("misspelled or unknown checks keys fail fast with KeyError on construction",
      strict_schema_validation_passed)

# Check strict schema validation on access c()
try:
    o_x_only.c("unknown_key_access")
    strict_access_validation_passed = False
except KeyError:
    strict_access_validation_passed = True
check("accessing unknown checks keys fails fast with KeyError via c()",
      strict_access_validation_passed)

# large ledger: append 500 entries, confirm integrity, tamper mid-chain, confirm detection
stress_ledger = Ledger()
for i in range(500):
    stress_ledger.append(type="event", object_id=f"obj-{i%5}", actor="sim",
                          authority="root", rationale=f"event {i}")
check("500-entry ledger verifies clean before tampering", stress_ledger.verify_integrity())

mid = list(stress_ledger._Ledger__entries)
tampered_mid = dataclasses.replace(mid[250], rationale="TAMPERED MID-CHAIN")
stress_ledger._Ledger__entries[250] = tampered_mid
check("tampering entry #250 of 500 is still detected (chain breaks from that point on)",
      not stress_ledger.verify_integrity())
check("entries before the tamper point are structurally unaffected (list length unchanged)",
      len(stress_ledger.entries()) == 500)


print()
print("=" * 70)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed, out of {len(PASS) + len(FAIL)} checks")
print("=" * 70)
if FAIL:
    print("FAILED CHECKS:")
    for f in FAIL:
        print(" -", f)
