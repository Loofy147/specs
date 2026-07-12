import pytest
from pydantic import ValidationError
from governance.models import (
    IdentityRecord, EvidenceBundle, VerificationPackage,
    UnderstandingLayer, RecoverabilityPlan, EvolutionPackage,
    GovernanceObject, LedgerEntry, ObjectTypeEnum, StatusEnum, SystemState
)
from governance.state_machine import (
    GovernanceStateMachine, GovernanceError, InvariantViolationError, ProtocolViolationError
)

# --- Helper Fixtures ---

@pytest.fixture
def initial_draft_object():
    return GovernanceObject(
        object_id="GOV-OBJ-100",
        object_type=ObjectTypeEnum.STATE_TRANSITION,
        status=StatusEnum.DRAFT,
        version=1,
        parent_reference="ROOT-0",
        provenance="CI/CD Build Pipeline",
        timestamps={"created": "2026-07-12T12:00:00Z"},
        signatures=[]
    )

@pytest.fixture
def base_system_state(initial_draft_object):
    return SystemState(
        current_object=initial_draft_object,
        ledger=[],
        active_protocols=["Canonicalization", "Contestation", "Drift"],
        drift_metrics={},
        trust_level="HIGH",
        is_emergency=False,
        history=[]
    )


# --- Model Validation & Dependency Tests ---

def test_governance_object_dependency_validation():
    # Valid model with no higher dependencies (level 1 only)
    obj = GovernanceObject(
        object_id="GOV-1",
        object_type=ObjectTypeEnum.IDENTITY_RECORD,
        status=StatusEnum.DRAFT,
        version=1,
        parent_reference="ROOT-0",
        provenance="Author",
        signatures=[]
    )
    assert obj is not None

    # Invalid: has understanding_layer but missing evidence_bundle (broken dependency chain)
    with pytest.raises(ValidationError) as excinfo:
        GovernanceObject(
            object_id="GOV-2",
            object_type=ObjectTypeEnum.IDENTITY_RECORD,
            status=StatusEnum.CANONICAL,
            version=1,
            parent_reference="ROOT-0",
            provenance="Author",
            understanding_layer=UnderstandingLayer(
                purpose_summary="Explain purpose of this state change",
                rule_architecture_summary="Arch summary",
                critical_path_explanation="Critical path info",
                major_risks=[],
                current_uncertainties=[],
                operational_boundaries=[]
            ),
            signatures=[]
        )
    assert "Artifact dependency order violated" in str(excinfo.value)


def test_canonical_object_validation():
    # Draft is allowed to be sparse
    draft_obj = GovernanceObject(
        object_id="GOV-3",
        object_type=ObjectTypeEnum.STATE_TRANSITION,
        status=StatusEnum.DRAFT,
        version=1,
        parent_reference="ROOT-0",
        provenance="Author"
    )
    assert draft_obj is not None

    # CANONICAL requires complete required artifacts, timestamps, and active authority signatures
    with pytest.raises(ValidationError) as excinfo:
        GovernanceObject(
            object_id="GOV-3",
            object_type=ObjectTypeEnum.STATE_TRANSITION,
            status=StatusEnum.CANONICAL,
            version=1,
            parent_reference="ROOT-0",
            provenance="Author"
        )
    assert "Canonicalization Rule Violated" in str(excinfo.value)


# --- Transition Contract Tests ---

def test_draft_to_provisional_transition(base_system_state):
    gsm = GovernanceStateMachine(base_system_state)
    assert gsm.state.current_object.status == StatusEnum.DRAFT

    # Fail: missing evidence bundle & scope
    with pytest.raises(ProtocolViolationError):
        gsm.transition_to(StatusEnum.PROVISIONAL, reason="First step")

    # Valid Provisional transition action
    action_obj = GovernanceObject(
        object_id="GOV-OBJ-100",
        object_type=ObjectTypeEnum.STATE_TRANSITION,
        status=StatusEnum.PROVISIONAL,
        version=2,
        parent_reference="GOV-OBJ-100",
        provenance="CI/CD Build Pipeline",
        evidence_bundle=EvidenceBundle(
            claim_being_supported="State draft is functional",
            source_provenance="Unit Tests",
            relevance_basis="Basis",
            limitations="None",
            confidence_level=0.95,
            contestation_path="/path"
        ),
        understanding_layer=UnderstandingLayer(
            purpose_summary="Transition system to provisional mode for testing",
            rule_architecture_summary="Arch description",
            critical_path_explanation="Critical path flow",
            operational_boundaries=["Boundary 1"]
        )
    )

    gsm.transition_to(StatusEnum.PROVISIONAL, reason="Transition to Provisional", action_obj=action_obj)
    assert gsm.state.current_object.status == StatusEnum.PROVISIONAL
    assert len(gsm.state.ledger) == 1
    assert gsm.state.ledger[0].previous_status == StatusEnum.DRAFT
    assert gsm.state.ledger[0].new_status == StatusEnum.PROVISIONAL


def test_provisional_to_canonical_transition(base_system_state):
    gsm = GovernanceStateMachine(base_system_state)
    # Set state as PROVISIONAL
    gsm.state.current_object.status = StatusEnum.PROVISIONAL

    # Incomplete artifacts
    with pytest.raises(ProtocolViolationError):
        gsm.transition_to(StatusEnum.CANONICAL, reason="Publish to canonical")

    # Compliant canonical action
    action_obj = GovernanceObject(
        object_id="GOV-OBJ-100",
        object_type=ObjectTypeEnum.STATE_TRANSITION,
        status=StatusEnum.CANONICAL,
        version=2,
        parent_reference="GOV-OBJ-100",
        provenance="CI/CD Build Pipeline",
        evidence_bundle=EvidenceBundle(
            claim_being_supported="Full system state is stable",
            source_provenance="Automation Tests",
            relevance_basis="Relevance basis of evidence",
            limitations="None",
            confidence_level=0.98,
            contestation_path="/contestation/100"
        ),
        verification_package=VerificationPackage(
            verification_methods=["e2e-integration-tests"],
            independence_analysis="QA independent signoff",
            test_results={"passed": 12, "failed": 0},
            adversarial_results={},
            semantic_equivalence_status="IDENTICAL",
            verifier_attestations=["reviewer-signature-01"]
        ),
        understanding_layer=UnderstandingLayer(
            purpose_summary="Full release audit and architectural summary",
            rule_architecture_summary="Arch description of canonical release",
            critical_path_explanation="Critical path runs cleanly",
            operational_boundaries=["None"]
        ),
        recoverability_plan=RecoverabilityPlan(
            failure_triggers=["Test failure"],
            containment_actions=["Rollback version"],
            rollback_mechanism="Standard Git rollback",
            recovery_steps=["Review logs"],
            restoration_criteria=["All tests clear"],
            audit_trail_requirements=["Read-only audit database logging"]
        ),
        timestamps={"creation": "2026-07-12T12:00:00Z", "activation": "2026-07-12T14:00:00Z"},
        signatures=["admin-attestation-signature"]
    )

    gsm.transition_to(StatusEnum.CANONICAL, reason="Authorize Canonical Status", action_obj=action_obj)
    assert gsm.state.current_object.status == StatusEnum.CANONICAL
    assert gsm.state.ledger[0].new_status == StatusEnum.CANONICAL


def test_contestation_and_containment_transitions(base_system_state):
    gsm = GovernanceStateMachine(base_system_state)
    gsm.state.current_object.status = StatusEnum.CANONICAL

    # Challenge
    gsm.challenge_object("challenge-102", "Telemetry indicates memory leaks.", "Telemetry logs #45")
    assert gsm.state.current_object.status == StatusEnum.CONTESTED
    assert gsm.state.current_object.contestation_state == "challenge-102"
    assert len(gsm.state.ledger) == 1
    assert gsm.state.ledger[0].new_status == StatusEnum.CONTESTED

    # Drift triggers CONTAINED state
    gsm.state.current_object.status = StatusEnum.CANONICAL
    gsm.trigger_containment("High divergency in verifier node metrics.", "node_divergence", 0.18, 0.10)
    assert gsm.state.current_object.status == StatusEnum.CONTAINED
    assert gsm.state.is_emergency is True


def test_emergency_recovery_flow(base_system_state):
    gsm = GovernanceStateMachine(base_system_state)
    gsm.state.current_object.status = StatusEnum.CONTAINED

    # Invalid: missing recoverability plan or recovery steps
    with pytest.raises(ProtocolViolationError):
        gsm.transition_to(StatusEnum.RECOVERY, reason="Begin repair")

    # Compliant recovery action
    recovery_action = GovernanceObject(
        object_id="GOV-OBJ-100",
        object_type=ObjectTypeEnum.STATE_TRANSITION,
        status=StatusEnum.RECOVERY,
        version=2,
        parent_reference="GOV-OBJ-100",
        provenance="Security Team",
        evidence_bundle=EvidenceBundle(
            claim_being_supported="Recovery is active",
            source_provenance="Security Team",
            relevance_basis="Basis",
            limitations="None",
            confidence_level=1.0,
            contestation_path="/path"
        ),
        verification_package=VerificationPackage(
            verification_methods=["audit"],
            independence_analysis="QA review",
            test_results={},
            adversarial_results={},
            semantic_equivalence_status="OK",
            verifier_attestations=["review-sig"]
        ),
        understanding_layer=UnderstandingLayer(
            purpose_summary="Comprehensive recovery explanation log",
            rule_architecture_summary="Audit summary of system nodes",
            critical_path_explanation="None",
            operational_boundaries=[]
        ),
        recoverability_plan=RecoverabilityPlan(
            failure_triggers=["Drift trigger"],
            containment_actions=["Audit logs"],
            rollback_mechanism="Rollback tool",
            recovery_steps=["Reset nodes", "Rerun verifier checks"],
            restoration_criteria=["All verifications pass"],
            audit_trail_requirements=["Write logs"]
        )
    )

    gsm.transition_to(StatusEnum.RECOVERY, reason="Initiate recovery repairs", action_obj=recovery_action)
    assert gsm.state.current_object.status == StatusEnum.RECOVERY


def test_deprecation_and_revocation(base_system_state):
    gsm = GovernanceStateMachine(base_system_state)
    gsm.state.current_object.status = StatusEnum.CANONICAL

    # Deprecate
    gsm.transition_to(StatusEnum.DEPRECATED, reason="Retire legacy component")
    assert gsm.state.current_object.status == StatusEnum.DEPRECATED
    assert "deprecated" in gsm.state.current_object.timestamps

    # Revoke
    gsm.state.current_object.status = StatusEnum.CANONICAL
    gsm.transition_to(StatusEnum.REVOKED, reason="Invalidated due to security keys breach")
    assert gsm.state.current_object.status == StatusEnum.REVOKED
    assert "revoked" in gsm.state.current_object.timestamps
