import pytest
import copy
from pydantic import ValidationError
from governance.models import (
    IdentityRecord, EvidenceBundle, VerificationPackage,
    UnderstandingLayer, RecoverabilityPlan, EvolutionPackage,
    GovernanceAction, SystemState, SystemStateEnum
)
from governance.state_machine import (
    GovernanceStateMachine, GovernanceError, InvariantViolationError, ProtocolViolationError
)

# --- Helper Fixtures ---

@pytest.fixture
def base_identity():
    return IdentityRecord(
        system_identifier="SYS-A",
        canonical_state_identifier="STATE-0",
        lineage_reference="ROOT-0",
        preserved_invariants=["Identity", "Evidence", "Verification", "Understanding", "Recoverability"],
        declared_changes=["Initial genesis setup"],
        unresolved_continuity_risks=[]
    )

@pytest.fixture
def draft_state(base_identity):
    return SystemState(
        runtime_state=SystemStateEnum.DRAFT,
        identity_record=base_identity,
        active_protocols=["Canonicalization", "Contestation", "Recursion", "Upgrade", "Drift"],
        drift_metrics={},
        trust_level="HIGH",
        is_emergency=False,
        history=[]
    )

@pytest.fixture
def compliant_action_data():
    return {
        "action_type": "STANDARD",
        "identity_record": {
            "system_identifier": "SYS-A",
            "canonical_state_identifier": "STATE-1",
            "lineage_reference": "STATE-0",
            "preserved_invariants": ["Identity", "Evidence"],
            "declared_changes": ["Update schema validation rules"],
            "unresolved_continuity_risks": []
        },
        "evidence_bundle": {
            "claim_being_supported": "Verification tool update is safe and compliant",
            "source_provenance": "CI/CD automated pipeline build #34",
            "relevance_basis": "Shows matching tests and independent verification",
            "limitations": "Does not cover legacy hardware integrations",
            "confidence_level": 0.95,
            "contestation_path": "/contestation/SYS-A/STATE-1"
        },
        "verification_package": {
            "verification_methods": ["automated-unit-tests", "manual-peer-review"],
            "independence_analysis": "Verified by independent QA team and pipeline validation",
            "test_results": {"passed": 42, "failed": 0, "total": 42},
            "adversarial_results": {"fuzzing": "passed", "red-team": "no vulnerabilities found"},
            "semantic_equivalence_status": "IDENTICAL",
            "verifier_attestations": ["attestation-signature-qa-lead-01"]
        },
        "understanding_layer": {
            "purpose_summary": "This action updates the system schema validators for enhanced compliance tracking.",
            "rule_architecture_summary": "Updates models.py with strict Pydantic field validation controls.",
            "critical_path_explanation": "Critical path runs through Pydantic validators and the canonical state machine.",
            "major_risks": ["Minor schema migration overhead during high load"],
            "current_uncertainties": ["None"],
            "operational_boundaries": ["Limits validator updates to non-breaking change definitions"]
        },
        "recoverability_plan": {
            "failure_triggers": ["State machine rejects valid action structures"],
            "containment_actions": ["Rollback model imports to version 1.1.2"],
            "rollback_mechanism": "Git checkout tag v1.1.2 and re-verify",
            "recovery_steps": ["Trigger containment actions", "Verify prior state continuity", "Revalidate dependencies"],
            "restoration_criteria": ["All automated unit tests pass in production sandbox"],
            "audit_trail_requirements": ["Logs must be written to read-only compliance storage"]
        }
    }


# --- Artifact Dependency Order Tests ---

def test_artifact_dependency_order_validation():
    # Valid order: ID + Evidence + Verification
    action_ok = GovernanceAction(
        action_type="PROPOSAL",
        identity_record=IdentityRecord(
            system_identifier="SYS-A",
            canonical_state_identifier="STATE-1",
            lineage_reference="STATE-0"
        ),
        evidence_bundle=EvidenceBundle(
            claim_being_supported="Support proposal",
            source_provenance="Source",
            relevance_basis="Basis",
            limitations="None",
            confidence_level=0.9,
            contestation_path="/path"
        ),
        verification_package=VerificationPackage(
            verification_methods=["unit"],
            independence_analysis="QA",
            test_results={},
            adversarial_results={},
            semantic_equivalence_status="OK",
            verifier_attestations=["A1"]
        )
    )
    assert action_ok is not None

    # Invalid order: has Verification Package but no Evidence Bundle (dependency broken)
    with pytest.raises(ValidationError) as excinfo:
        GovernanceAction(
            action_type="PROPOSAL",
            identity_record=IdentityRecord(
                system_identifier="SYS-A",
                canonical_state_identifier="STATE-1",
                lineage_reference="STATE-0"
            ),
            verification_package=VerificationPackage(
                verification_methods=["unit"],
                independence_analysis="QA",
                test_results={},
                adversarial_results={},
                semantic_equivalence_status="OK",
                verifier_attestations=["A1"]
            )
        )
    assert "Artifact dependency order violated" in str(excinfo.value)


# --- System Runtime State Transition Tests ---

def test_draft_to_provisional_transition(draft_state):
    gsm = GovernanceStateMachine(draft_state)
    assert gsm.state.runtime_state == SystemStateEnum.DRAFT

    # Attempt transition without required action artifacts
    bad_action = GovernanceAction(
        action_type="TRANSITION",
        identity_record=gsm.state.identity_record
    )
    with pytest.raises(ProtocolViolationError):
        gsm.transition_to(SystemStateEnum.PROVISIONAL, action=bad_action)

    # Compliant transition action (ID + EV + VP + UL)
    good_action = GovernanceAction(
        action_type="TRANSITION",
        identity_record=gsm.state.identity_record,
        evidence_bundle=EvidenceBundle(
            claim_being_supported="Transition proposal",
            source_provenance="Internal Team",
            relevance_basis="Basis of transition",
            limitations="None",
            confidence_level=0.9,
            contestation_path="/path"
        ),
        verification_package=VerificationPackage(
            verification_methods=["dry-run"],
            independence_analysis="Internal check",
            test_results={},
            adversarial_results={},
            semantic_equivalence_status="OK",
            verifier_attestations=["signer-0"]
        ),
        understanding_layer=UnderstandingLayer(
            purpose_summary="Explain the transition in detail",
            rule_architecture_summary="Architecture info",
            critical_path_explanation="Critical path info",
            operational_boundaries=["Scope limit 1"]
        )
    )

    gsm.transition_to(SystemStateEnum.PROVISIONAL, action=good_action)
    assert gsm.state.runtime_state == SystemStateEnum.PROVISIONAL


def test_provisional_to_canonical_transition(draft_state, compliant_action_data):
    # Setup state in PROVISIONAL
    gsm = GovernanceStateMachine(draft_state)
    gsm.state.runtime_state = SystemStateEnum.PROVISIONAL

    # Action with unresolved critical risks
    risky_action_data = copy.deepcopy(compliant_action_data)
    risky_action_data["identity_record"]["unresolved_continuity_risks"] = ["Critical security risk"]
    risky_action = GovernanceAction(**risky_action_data)

    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.transition_to(SystemStateEnum.CANONICAL, action=risky_action)
    assert "unresolved continuity risks exist" in str(excinfo.value)

    # Compliant Canonical action
    compliant_action = GovernanceAction(**compliant_action_data)
    gsm.transition_to(SystemStateEnum.CANONICAL, action=compliant_action)
    assert gsm.state.runtime_state == SystemStateEnum.CANONICAL
    assert gsm.state.is_canonical is True


# --- Decision Gate and Executions ---

def test_decision_gate_and_executions(draft_state, compliant_action_data):
    gsm = GovernanceStateMachine(draft_state)
    action = GovernanceAction(**compliant_action_data)

    # 1. Blocked when not Canonical
    assert gsm.state.runtime_state == SystemStateEnum.DRAFT
    assert gsm.can_execute_decision(action) is False
    with pytest.raises(ProtocolViolationError):
        gsm.execute_decision(action)

    # 2. Setup Canonical state
    gsm.state.runtime_state = SystemStateEnum.CANONICAL
    # Fill required artifacts on state to make it canonical
    gsm.state.last_evidence_bundle = action.evidence_bundle
    gsm.state.last_verification_package = action.verification_package
    gsm.state.last_understanding_layer = action.understanding_layer
    gsm.state.last_recoverability_plan = action.recoverability_plan
    assert gsm.state.is_canonical is True

    # 3. Successful execution when Canonical and artifacts present
    assert gsm.can_execute_decision(action) is True
    new_state = gsm.execute_decision(action)
    assert new_state.runtime_state == SystemStateEnum.CANONICAL


# --- Contestation Protocol & Transition ---

def test_contestation_and_transition(draft_state, compliant_action_data):
    gsm = GovernanceStateMachine(draft_state)
    # Put state into Canonical
    action = GovernanceAction(**compliant_action_data)
    gsm.state.runtime_state = SystemStateEnum.CANONICAL
    gsm.state.last_evidence_bundle = action.evidence_bundle
    gsm.state.last_verification_package = action.verification_package
    gsm.state.last_understanding_layer = action.understanding_layer
    gsm.state.last_recoverability_plan = action.recoverability_plan

    # Challenge
    outcome = gsm.challenge_artifact(
        target_artifact="last_evidence_bundle",
        basis="Telemetry suggests inaccuracies.",
        evidence="Telemetry log #102",
        burden_of_proof="QA verification"
    )

    assert gsm.state.runtime_state == SystemStateEnum.CONTESTED
    assert outcome["provisional_status"] == "CHALLENGED"


# --- Drift, Emergency, and Recovery Transitions ---

def test_drift_triggers_contained_state(draft_state):
    gsm = GovernanceStateMachine(draft_state)
    gsm.state.runtime_state = SystemStateEnum.CANONICAL

    # Metric drift over threshold
    gsm.record_metric_drift("monitor_divergence", 0.15, 0.10)
    assert gsm.state.runtime_state == SystemStateEnum.CONTAINED


def test_emergency_declaration_triggers_contained_state(draft_state):
    gsm = GovernanceStateMachine(draft_state)
    gsm.state.runtime_state = SystemStateEnum.CANONICAL

    # Declare Emergency
    gsm.declare_emergency(
        trigger="Compromised credentials detected",
        scope="Lockdown transition controls",
        duration_hours=12
    )
    assert gsm.state.runtime_state == SystemStateEnum.CONTAINED


def test_emergency_resolution_and_recovery_flow(draft_state):
    gsm = GovernanceStateMachine(draft_state)
    gsm.state.runtime_state = SystemStateEnum.CONTAINED

    # Resolve emergency substantively
    gsm.resolve_emergency(
        "Substantive review complete. All systems secure and audited successfully."
    )
    # resolve_emergency transitions CONTAINED -> RECOVERY
    assert gsm.state.runtime_state == SystemStateEnum.RECOVERY

    # Transition RECOVERY -> CANONICAL
    recovery_resolution_action = GovernanceAction(
        action_type="RECOVERY",
        identity_record=gsm.state.identity_record,
        evidence_bundle=EvidenceBundle(
            claim_being_supported="Recovery is safe and complete",
            source_provenance="Security Team",
            relevance_basis="Revalidation logs",
            limitations="None",
            confidence_level=0.95,
            contestation_path="/contestation/recovery"
        ),
        verification_package=VerificationPackage(
            verification_methods=["all-clear-verification"],
            independence_analysis="QA independent reviewer",
            test_results={"failed": 0, "passed": 10},
            adversarial_results={},
            semantic_equivalence_status="IDENTICAL",
            verifier_attestations=["signature-verifier-01"]
        ),
        understanding_layer=UnderstandingLayer(
            purpose_summary="Transition system back to standard CANONICAL operations",
            rule_architecture_summary="Restore state rules",
            critical_path_explanation="Restoration of canonical access",
            operational_boundaries=["Boundaries unchanged"]
        ),
        recoverability_plan=RecoverabilityPlan(
            failure_triggers=["Validation failure"],
            containment_actions=["Rollback to recovery mode"],
            rollback_mechanism="Standard mechanism",
            recovery_steps=["Review"],
            restoration_criteria=["All clear"],
            audit_trail_requirements=["Compliance logging"]
        ),
        evolution_package=EvolutionPackage(
            continuity_proof="Continuous lineage proof back to state 0.",
            preserved_invariants=["Identity"],
            modified_invariants=[],
            removed_capabilities=[],
            new_capabilities=[],
            second_order_impact_assessment="No performance impact.",
            recovery_and_rollback_guarantees="Guaranteed safety",
            independent_attestation="Attested by QA lead"
        )
    )

    gsm.transition_to(SystemStateEnum.CANONICAL, action=recovery_resolution_action)
    assert gsm.state.runtime_state == SystemStateEnum.CANONICAL
