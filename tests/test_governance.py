import pytest
from pydantic import ValidationError
from governance.models import (
    IdentityRecord, EvidenceBundle, VerificationPackage,
    UnderstandingLayer, RecoverabilityPlan, EvolutionPackage,
    GovernanceAction, SystemState
)
from governance.state_machine import (
    GovernanceStateMachine, GovernanceError, InvariantViolationError, ProtocolViolationError
)

# --- Helper Fixtures ---

@pytest.fixture
def genesis_identity():
    return IdentityRecord(
        system_identifier="SYS-A",
        canonical_state_identifier="GENESIS-0",
        lineage_reference="ROOT-0",
        preserved_invariants=["Identity", "Evidence", "Verification", "Understanding", "Recoverability"],
        declared_changes=["Initial genesis setup"],
        unresolved_continuity_risks=[]
    )

@pytest.fixture
def genesis_state(genesis_identity):
    return SystemState(
        identity_record=genesis_identity,
        active_protocols=["Canonicalization", "Contestation", "Recursion", "Upgrade", "Drift"],
        drift_metrics={},
        trust_level="HIGH",
        is_emergency=False,
        history=[]
    )

@pytest.fixture
def standard_action_data():
    return {
        "action_type": "STANDARD",
        "identity_record": {
            "system_identifier": "SYS-A",
            "canonical_state_identifier": "STATE-1",
            "lineage_reference": "GENESIS-0",
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

# --- Schema and Model Validation Tests ---

def test_valid_identity_record(genesis_identity):
    assert genesis_identity.system_identifier == "SYS-A"
    assert genesis_identity.canonical_state_identifier == "GENESIS-0"

def test_invalid_identity_record():
    with pytest.raises(ValidationError):
        # Empty system_identifier
        IdentityRecord(
            system_identifier="",
            canonical_state_identifier="GENESIS-0",
            lineage_reference="ROOT-0"
        )

def test_evidence_bundle_confidence_validation():
    # Invalid confidence (above 1.0)
    with pytest.raises(ValidationError):
        EvidenceBundle(
            claim_being_supported="Claim",
            source_provenance="Source",
            relevance_basis="Basis",
            limitations="Limitations",
            confidence_level=1.1,
            contestation_path="Path"
        )
    # Invalid confidence (below 0.0)
    with pytest.raises(ValidationError):
        EvidenceBundle(
            claim_being_supported="Claim",
            source_provenance="Source",
            relevance_basis="Basis",
            limitations="Limitations",
            confidence_level=-0.1,
            contestation_path="Path"
        )

def test_governance_action_enforcement_rule(standard_action_data):
    # Valid standard action (no evolution package needed)
    action = GovernanceAction(**standard_action_data)
    assert action.action_type == "STANDARD"
    assert action.evolution_package is None

    # Invalid action type
    bad_data = standard_action_data.copy()
    bad_data["action_type"] = "INVALID"
    with pytest.raises(ValidationError):
        GovernanceAction(**bad_data)

    # Evolution action without evolution package
    evo_data_bad = standard_action_data.copy()
    evo_data_bad["action_type"] = "EVOLUTION"
    with pytest.raises(ValidationError):
        GovernanceAction(**evo_data_bad)

    # Valid evolution action with evolution package
    evo_data_good = standard_action_data.copy()
    evo_data_good["action_type"] = "EVOLUTION"
    evo_data_good["evolution_package"] = {
        "continuity_proof": "Proof of identity preservation and zero integrity leaks.",
        "preserved_invariants": ["Identity", "Evidence", "Verification"],
        "modified_invariants": [],
        "removed_capabilities": [],
        "new_capabilities": ["Support for automatic JSON Schema emission"],
        "second_order_impact_assessment": "Increases transparency for human auditors.",
        "recovery_and_rollback_guarantees": "Supports complete database schema rollback in under 30 seconds.",
        "independent_attestation": "Attested by lead security auditor on date 2024-07-12."
    }
    action_evo = GovernanceAction(**evo_data_good)
    assert action_evo.action_type == "EVOLUTION"
    assert action_evo.evolution_package is not None

# --- State Machine & Canonicalization Tests ---

def test_valid_state_transition(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    action = GovernanceAction(**standard_action_data)

    new_state = gsm.transition(action)

    assert gsm.get_current_state() == new_state
    assert new_state.identity_record.canonical_state_identifier == "STATE-1"
    assert new_state.last_evidence_bundle.claim_being_supported == "Verification tool update is safe and compliant"
    assert len(new_state.history) == 1
    assert new_state.history[0]["previous_state_id"] == "GENESIS-0"
    assert new_state.history[0]["new_state_id"] == "STATE-1"

def test_transition_lineage_break(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    # Break lineage reference
    standard_action_data["identity_record"]["lineage_reference"] = "WRONG-PARENT"
    action = GovernanceAction(**standard_action_data)

    with pytest.raises(InvariantViolationError) as excinfo:
        gsm.transition(action)
    assert "Lineage break" in str(excinfo.value)

def test_transition_system_mismatch(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    # Change system identifier
    standard_action_data["identity_record"]["system_identifier"] = "SYS-B"
    action = GovernanceAction(**standard_action_data)

    with pytest.raises(InvariantViolationError) as excinfo:
        gsm.transition(action)
    assert "System mismatch" in str(excinfo.value)

def test_transition_low_confidence(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    # Confidence level below 0.5
    standard_action_data["evidence_bundle"]["confidence_level"] = 0.49
    action = GovernanceAction(**standard_action_data)

    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.transition(action)
    assert "confidence level too low" in str(excinfo.value)

def test_transition_failing_verification(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    # Add failure to test_results
    standard_action_data["verification_package"]["test_results"]["failed"] = 1
    action = GovernanceAction(**standard_action_data)

    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.transition(action)
    assert "test results contain failures" in str(excinfo.value)

def test_transition_missing_authority(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)
    # Clear verifier attestations
    standard_action_data["verification_package"]["verifier_attestations"] = []
    action = GovernanceAction(**standard_action_data)

    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.transition(action)
    assert "Authority rules check failed" in str(excinfo.value)

# --- Contestation Protocol Tests ---

def test_contestation_protocol(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    assert gsm.state.trust_level == "HIGH"

    outcome = gsm.challenge_artifact(
        target_artifact="evidence_bundle",
        basis="Confidence score is artificially inflated by outdated pipeline telemetry.",
        evidence="Telemetry log log-2024-07-11.txt showing 20% timeout rates.",
        burden_of_proof="Independent verification team audit."
    )

    assert gsm.state.trust_level == "DOWNGRADED"
    assert outcome["provisional_status"] == "CHALLENGED"
    assert len(gsm.state.history) == 1
    assert gsm.state.history[0]["event"] == "CONTESTATION_FILED"
    assert gsm.state.history[0]["target"] == "evidence_bundle"

def test_contestation_protocol_invalid(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    with pytest.raises(ProtocolViolationError):
        gsm.challenge_artifact("", "", "", "")

# --- Recursion Control Protocol Tests ---

def test_recursion_control(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    # Under limit
    assert gsm.evaluate_recursive_process(current_depth=3, max_depth=5) is True

    # Exceeding limit
    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.evaluate_recursive_process(current_depth=6, max_depth=5)
    assert "Recursion depth limit exceeded" in str(excinfo.value)

# --- Upgrade Control Protocol Tests ---

def test_upgrade_control_protocol_workflow(genesis_state, standard_action_data):
    gsm = GovernanceStateMachine(genesis_state)

    # 1. Propose Upgrade
    gsm.propose_upgrade("UPGRADE-01", "Upgrade to next-generation metadata schema.")
    assert gsm._upgrade_proposal["stage"] == "PROPOSAL"

    # 2. Sequential advancements
    gsm.advance_upgrade_stage("IMPACT_ASSESSMENT")
    assert gsm._upgrade_proposal["stage"] == "IMPACT_ASSESSMENT"

    gsm.advance_upgrade_stage("VERIFICATION")
    gsm.advance_upgrade_stage("ATTESTATION")
    gsm.advance_upgrade_stage("LIMITED_ACTIVATION")
    gsm.advance_upgrade_stage("MONITORING")
    assert gsm._upgrade_proposal["stage"] == "MONITORING"

    # 3. Commit via valid EVOLUTION action
    evo_data = standard_action_data.copy()
    evo_data["action_type"] = "EVOLUTION"
    evo_data["evolution_package"] = {
        "continuity_proof": "Proof of zero invariant loss across upgrade boundaries.",
        "preserved_invariants": ["Identity", "Evidence"],
        "modified_invariants": [],
        "removed_capabilities": [],
        "new_capabilities": ["Feature-Z"],
        "second_order_impact_assessment": "No performance degradation found.",
        "recovery_and_rollback_guarantees": "Supports live instant rollback to GENESIS-0.",
        "independent_attestation": "Attested by QA Security Lead."
    }
    action_evo = GovernanceAction(**evo_data)
    new_state = gsm.transition(action_evo)

    assert gsm._upgrade_proposal is None
    assert new_state.last_evolution_package is not None
    assert new_state.last_evolution_package.new_capabilities == ["Feature-Z"]

def test_upgrade_control_out_of_order_stages(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    gsm.propose_upgrade("UPGRADE-01", "Sample upgrade")

    # Try advancing directly to ATTESTATION, skipping IMPACT_ASSESSMENT and VERIFICATION
    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.advance_upgrade_stage("ATTESTATION")
    assert "Invalid stage transition" in str(excinfo.value)

def test_upgrade_control_abort_and_rollback(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    gsm.propose_upgrade("UPGRADE-01", "Sample upgrade")
    gsm.advance_upgrade_stage("IMPACT_ASSESSMENT")

    abort_record = gsm.abort_upgrade("Found critical regression in dry-run environment.")

    assert gsm._upgrade_proposal is None
    assert abort_record["action"] == "ROLLBACK"
    assert gsm.state.history[0]["event"] == "UPGRADE_ABORTED"
    assert gsm.state.history[0]["record"]["reason"] == "Found critical regression in dry-run environment."

# --- Drift and Metric Control Protocol Tests ---

def test_drift_and_metric_control(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    assert gsm.state.trust_level == "HIGH"

    # Under threshold
    gsm.record_metric_drift("verification_tool_divergence", 0.05, 0.10)
    assert gsm.state.trust_level == "HIGH"

    # Over threshold
    gsm.record_metric_drift("verification_tool_divergence", 0.12, 0.10)
    assert gsm.state.trust_level == "DOWNGRADED"
    assert any(h["event"] == "DRIFT_DETECTED" for h in gsm.state.history)

# --- Containment and Emergency Protocol Tests ---

def test_emergency_protocol(genesis_state):
    gsm = GovernanceStateMachine(genesis_state)
    assert gsm.state.is_emergency is False

    # Declare Emergency
    gsm.declare_emergency(
        trigger="Unrecognized state transition detected by monitoring tool.",
        scope="State transitions restricted to READ-ONLY and emergency containments.",
        duration_hours=24
    )
    assert gsm.state.is_emergency is True
    assert gsm.state.history[0]["event"] == "EMERGENCY_DECLARED"

    # Resolve with inadequate retrospective review
    with pytest.raises(ProtocolViolationError) as excinfo:
        gsm.resolve_emergency("Too short.")
    assert "Retrospective audit must be substantive" in str(excinfo.value)

    # Resolve with substantive retrospective review
    gsm.resolve_emergency(
        "Substantive retrospective audit complete. Verified zero data corruption or un-audited state mutation."
    )
    assert gsm.state.is_emergency is False
    assert gsm.state.history[1]["event"] == "EMERGENCY_RESOLVED"
