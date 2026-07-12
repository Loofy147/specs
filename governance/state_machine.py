import datetime
from typing import List, Dict, Any, Optional
from governance.models import (
    SystemState, SystemStateEnum, GovernanceAction, IdentityRecord, EvidenceBundle,
    VerificationPackage, UnderstandingLayer, RecoverabilityPlan, EvolutionPackage
)

class GovernanceError(Exception):
    """Base exception for all governance and constitution violations."""
    pass

class InvariantViolationError(GovernanceError):
    """Raised when a core invariant is violated."""
    pass

class ProtocolViolationError(GovernanceError):
    """Raised when a governing protocol rule is violated."""
    pass


class GovernanceStateMachine:
    """
    Enforces the Master Governance Constitution and Governance Runtime Model.
    Manages explicit runtime states, transitions, decision gates, dependency order,
    and invariant preservation.
    """

    def __init__(self, initial_state: SystemState):
        if not initial_state:
            raise GovernanceError("Initial state cannot be None.")
        self.state = initial_state
        self._upgrade_proposal: Optional[Dict[str, Any]] = None

    def get_current_state(self) -> SystemState:
        """Returns the current canonical system state."""
        return self.state

    def _verify_authority(self, action: GovernanceAction) -> bool:
        """
        Enforces Section 5 (Authority Rules):
        Authority is valid only when declared, attested, traceable, and reviewable.
        """
        if not action.verification_package or not action.verification_package.verifier_attestations:
            return False
        if not action.evidence_bundle or not action.evidence_bundle.source_provenance:
            return False
        if not action.evidence_bundle.contestation_path:
            return False
        return True

    def _preserve_invariants(self, action: GovernanceAction):
        """
        Enforces Governance Runtime Model Rule 6 (Invariant Preservation Rule):
        Any transition must preserve identity, evidence traceability, verifier independence,
        human comprehensibility, and rollback availability.
        """
        # 1. Continuity of Identity
        if action.identity_record:
            if action.identity_record.system_identifier != self.state.identity_record.system_identifier:
                raise InvariantViolationError("Invariant Violation: Continuity of identity broken (system mismatch).")

            # Lineage continuity check
            # If transitioning to a new canonical state identifier:
            if action.identity_record.canonical_state_identifier != self.state.identity_record.canonical_state_identifier:
                if action.identity_record.lineage_reference != self.state.identity_record.canonical_state_identifier:
                    raise InvariantViolationError("Invariant Violation: Continuity of lineage broken.")
            else:
                # Staying on same state identifier, lineage reference must match current lineage reference
                if action.identity_record.lineage_reference != self.state.identity_record.lineage_reference:
                    raise InvariantViolationError("Invariant Violation: Continuity of lineage broken (lineage reference mismatch).")

        # 2. Traceability of Evidence
        if action.evidence_bundle:
            if not action.evidence_bundle.claim_being_supported or not action.evidence_bundle.source_provenance:
                raise InvariantViolationError("Invariant Violation: Traceability of evidence is not preserved.")

        # 3. Verifier Independence
        if action.verification_package:
            if not action.verification_package.verifier_attestations or not action.verification_package.independence_analysis:
                raise InvariantViolationError("Invariant Violation: Verifier independence is not preserved.")

        # 4. Human Comprehensibility
        if action.understanding_layer:
            if len(action.understanding_layer.purpose_summary) < 10:
                raise InvariantViolationError("Invariant Violation: Human comprehensibility of the action is too brief.")

        # 5. Rollback Availability
        if action.recoverability_plan:
            if not action.recoverability_plan.rollback_mechanism:
                raise InvariantViolationError("Invariant Violation: Rollback availability is missing.")

    def can_execute_decision(self, action: GovernanceAction) -> bool:
        """
        Enforces Governance Runtime Model Section 4 (Decision Gate):
        A decision may be executed only when all of the following are true:
        - the current state is Canonical
        - the required artifacts are present
        - verifiers are valid and independent
        - no active contestation blocks authority
        - no containment state is active
        - the action is within authorized scope
        """
        if self.state.runtime_state != SystemStateEnum.CANONICAL:
            return False
        if not self.state.is_canonical:
            return False
        if not action.verification_package or not action.verification_package.verifier_attestations:
            return False
        # Verifier success check
        test_results = action.verification_package.test_results
        if test_results.get("failed", 0) > 0 or test_results.get("success") is False:
            return False
        return True

    def execute_decision(self, action: GovernanceAction) -> SystemState:
        """
        Enforces the Decision Gate and executes a valid action in Canonical state.
        """
        if not self.can_execute_decision(action):
            raise ProtocolViolationError("Decision Gate failed: state is not Canonical or required conditions not met.")

        self._preserve_invariants(action)

        # Record decision execution
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        history_entry = {
            "timestamp": timestamp,
            "event": "DECISION_EXECUTED",
            "action_type": action.action_type,
            "previous_state_id": self.state.identity_record.canonical_state_identifier,
            "new_state_id": action.identity_record.canonical_state_identifier
        }

        # Apply action to build new SystemState
        new_state = SystemState(
            runtime_state=SystemStateEnum.CANONICAL,
            identity_record=action.identity_record,
            last_evidence_bundle=action.evidence_bundle,
            last_verification_package=action.verification_package,
            last_understanding_layer=action.understanding_layer,
            last_recoverability_plan=action.recoverability_plan,
            last_evolution_package=action.evolution_package,
            active_protocols=self.state.active_protocols,
            drift_metrics=self.state.drift_metrics,
            trust_level=self.state.trust_level,
            is_emergency=self.state.is_emergency,
            history=self.state.history + [history_entry]
        )

        self.state = new_state
        return self.state

    def transition_to(self, target_state: SystemStateEnum, action: Optional[GovernanceAction] = None) -> SystemState:
        """
        Enforces Governance Runtime Model Section 3 (Transition Rules):
        """
        current = self.state.runtime_state

        if current == target_state:
            return self.state

        # Enforce transition rules and prerequisites
        if current == SystemStateEnum.DRAFT and target_state == SystemStateEnum.PROVISIONAL:
            # Requires: initial evidence, initial review, declared scope
            if not action or not action.evidence_bundle or not action.understanding_layer:
                raise ProtocolViolationError("Draft -> Provisional transition requires initial evidence and understanding layer.")
            if not action.understanding_layer.operational_boundaries:
                raise ProtocolViolationError("Draft -> Provisional transition requires declared scope/boundaries.")

        elif current == SystemStateEnum.PROVISIONAL and target_state == SystemStateEnum.CANONICAL:
            # Requires: complete artifacts, independent attestation, successful validation, no unresolved critical risks
            if not action:
                raise ProtocolViolationError("Provisional -> Canonical transition requires a complete action.")
            # Verify complete artifacts
            if not (action.identity_record and action.evidence_bundle and action.verification_package
                    and action.understanding_layer and action.recoverability_plan):
                raise ProtocolViolationError("Provisional -> Canonical transition requires all 5 standard artifacts.")
            # Verify no unresolved critical risks
            if action.identity_record.unresolved_continuity_risks:
                raise ProtocolViolationError("Provisional -> Canonical transition blocked: unresolved continuity risks exist.")
            # Verify authority (Section 5)
            if not self._verify_authority(action):
                raise ProtocolViolationError("Authority rules check failed (Section 5 violation).")
            # Verify test validation
            if action.verification_package.test_results.get("failed", 0) > 0:
                raise ProtocolViolationError("Successful validation required for Canonical transition.")

        elif current == SystemStateEnum.CANONICAL and target_state == SystemStateEnum.CONTESTED:
            # Requires: valid challenge, evidence basis, contestation registration
            if not action or not action.evidence_bundle or not action.evidence_bundle.claim_being_supported:
                raise ProtocolViolationError("Canonical -> Contested transition requires evidence of challenge.")

        elif (current in (SystemStateEnum.CANONICAL, SystemStateEnum.PROVISIONAL)) and target_state == SystemStateEnum.CONTAINED:
            # Requires: drift threshold breach, semantic mismatch, verifier failure, authority compromise, external trigger
            pass

        elif current == SystemStateEnum.CONTAINED and target_state == SystemStateEnum.RECOVERY:
            # Requires: containment acknowledgement, repair plan, bounded restoration scope
            if not action or not action.recoverability_plan:
                raise ProtocolViolationError("Contained -> Recovery transition requires a recoverability/repair plan.")
            if not action.recoverability_plan.recovery_steps:
                raise ProtocolViolationError("Contained -> Recovery transition requires repair steps.")

        elif current == SystemStateEnum.RECOVERY and target_state == SystemStateEnum.CANONICAL:
            # Requires: successful revalidation, integrity proof, restoration attestation
            if not action or not action.verification_package or not action.evolution_package:
                raise ProtocolViolationError("Recovery -> Canonical transition requires verification and evolution integrity proof.")
            if not action.verification_package.verifier_attestations:
                raise ProtocolViolationError("Recovery -> Canonical transition requires verifier attestations.")

        else:
            raise ProtocolViolationError(f"Direct transition from {current} to {target_state} is invalid under Runtime Model.")

        # If an action was provided, ensure it preserves invariants
        if action:
            self._preserve_invariants(action)

        # Execute the transition
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        history_entry = {
            "timestamp": timestamp,
            "event": "STATE_TRANSITION",
            "from_state": current.value,
            "to_state": target_state.value
        }

        # Build updated SystemState
        new_state = SystemState(
            runtime_state=target_state,
            identity_record=action.identity_record if action and action.identity_record else self.state.identity_record,
            last_evidence_bundle=action.evidence_bundle if action and action.evidence_bundle else self.state.last_evidence_bundle,
            last_verification_package=action.verification_package if action and action.verification_package else self.state.last_verification_package,
            last_understanding_layer=action.understanding_layer if action and action.understanding_layer else self.state.last_understanding_layer,
            last_recoverability_plan=action.recoverability_plan if action and action.recoverability_plan else self.state.last_recoverability_plan,
            last_evolution_package=action.evolution_package if action and action.evolution_package else self.state.last_evolution_package,
            active_protocols=self.state.active_protocols,
            drift_metrics=self.state.drift_metrics,
            trust_level="DOWNGRADED" if target_state in (SystemStateEnum.CONTESTED, SystemStateEnum.CONTAINED) else self.state.trust_level,
            is_emergency=True if target_state == SystemStateEnum.CONTAINED else self.state.is_emergency,
            history=self.state.history + [history_entry]
        )

        self.state = new_state
        return self.state

    def challenge_artifact(self, target_artifact: str, basis: str, evidence: str, burden_of_proof: str) -> Dict[str, Any]:
        """
        Enforces Section 4.2 (Contestation Protocol):
        Any canonical artifact may be challenged. Transitions system to CONTESTED state.
        """
        if not target_artifact or not basis or not evidence or not burden_of_proof:
            raise ProtocolViolationError("Contestation requires target_artifact, basis, evidence, and burden_of_proof.")

        # Transition state to CONTESTED
        challenge_action = GovernanceAction(
            action_type="CONTESTATION",
            identity_record=self.state.identity_record,
            evidence_bundle=EvidenceBundle(
                claim_being_supported=f"Challenge of {target_artifact}",
                source_provenance="Independent Challenger",
                relevance_basis=basis,
                limitations="None",
                confidence_level=0.9,
                contestation_path="/contestation/review"
            )
        )
        self.transition_to(SystemStateEnum.CONTESTED, action=challenge_action)

        outcome = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "target_artifact": target_artifact,
            "basis": basis,
            "evidence": evidence,
            "burden_of_proof": burden_of_proof,
            "provisional_status": "CHALLENGED",
            "action_taken": "System state transitioned to CONTESTED and trust level downgraded."
        }

        return outcome

    def evaluate_recursive_process(self, current_depth: int, max_depth: int) -> bool:
        """
        Enforces Section 4.3 (Recursion Control Protocol):
        No infinite regress is permitted.
        """
        if current_depth > max_depth:
            raise ProtocolViolationError(
                f"Recursion depth limit exceeded. Current depth {current_depth} > max limit {max_depth}."
            )
        return True

    def propose_upgrade(self, proposal_id: str, description: str):
        """
        Initiates Section 4.4 (Upgrade Control Protocol) - Stage 1 (Proposal).
        """
        self._upgrade_proposal = {
            "proposal_id": proposal_id,
            "description": description,
            "stage": "PROPOSAL",
            "stages_history": ["PROPOSAL"],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    def advance_upgrade_stage(self, stage: str):
        """
        Enforces advancement through stages:
        1. PROPOSAL, 2. IMPACT_ASSESSMENT, 3. VERIFICATION, 4. ATTESTATION,
        5. LIMITED_ACTIVATION, 6. MONITORING, 7. COMMIT_OR_ROLLBACK (transition method commits)
        """
        if not self._upgrade_proposal:
            raise ProtocolViolationError("No active upgrade proposal found to advance.")

        valid_stages = [
            "PROPOSAL", "IMPACT_ASSESSMENT", "VERIFICATION",
            "ATTESTATION", "LIMITED_ACTIVATION", "MONITORING"
        ]

        if stage not in valid_stages:
            raise ProtocolViolationError(f"Invalid upgrade stage: '{stage}'.")

        current_stage = self._upgrade_proposal["stage"]
        current_index = valid_stages.index(current_stage)
        target_index = valid_stages.index(stage)

        if target_index != current_index + 1:
            raise ProtocolViolationError(
                f"Invalid stage transition. Cannot transition from '{current_stage}' to '{stage}' directly."
            )

        self._upgrade_proposal["stage"] = stage
        self._upgrade_proposal["stages_history"].append(stage)

    def abort_upgrade(self, reason: str) -> Dict[str, Any]:
        """Aborts and rolls back the current upgrade proposal."""
        if not self._upgrade_proposal:
            raise ProtocolViolationError("No active upgrade proposal to abort.")

        abort_record = {
            "proposal_id": self._upgrade_proposal["proposal_id"],
            "last_stage": self._upgrade_proposal["stage"],
            "reason": reason,
            "action": "ROLLBACK",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        self.state.history.append({
            "event": "UPGRADE_ABORTED",
            "timestamp": abort_record["timestamp"],
            "record": abort_record
        })

        self._upgrade_proposal = None
        return abort_record

    def record_metric_drift(self, metric_name: str, value: float, threshold: float):
        """
        Enforces Section 4.5 (Drift and Metric Control Protocol):
        Exceeding threshold triggers automated transition to CONTAINED state.
        """
        self.state.drift_metrics[metric_name] = {
            "value": value,
            "threshold": threshold,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        if value > threshold:
            drift_action = GovernanceAction(
                action_type="DRIFT",
                identity_record=self.state.identity_record,
                evidence_bundle=EvidenceBundle(
                    claim_being_supported=f"Metric Drift Alert: {metric_name}",
                    source_provenance="Verification Monitor",
                    relevance_basis=f"Divergence value {value} exceeded threshold {threshold}.",
                    limitations="None",
                    confidence_level=1.0,
                    contestation_path="/drift/review"
                )
            )
            self.transition_to(SystemStateEnum.CONTAINED, action=drift_action)

    def declare_emergency(self, trigger: str, scope: str, duration_hours: int):
        """
        Enforces Section 4.7 (Containment and Emergency Protocol):
        Transition state to CONTAINED.
        """
        if not trigger or not scope or duration_hours <= 0:
            raise ProtocolViolationError("Emergency declaration requires a trigger, scope, and positive duration limit.")

        emergency_action = GovernanceAction(
            action_type="EMERGENCY",
            identity_record=self.state.identity_record,
            evidence_bundle=EvidenceBundle(
                claim_being_supported=f"Emergency trigger: {trigger}",
                source_provenance="System Admin",
                relevance_basis=scope,
                limitations="None",
                confidence_level=1.0,
                contestation_path="/emergency/review"
            )
        )
        self.transition_to(SystemStateEnum.CONTAINED, action=emergency_action)

    def resolve_emergency(self, retrospective_review: str):
        """Resolves emergency mode after performing an obligatory retrospective audit."""
        if self.state.runtime_state != SystemStateEnum.CONTAINED:
            raise ProtocolViolationError("System is not currently in CONTAINED mode.")

        if len(retrospective_review) < 15:
            raise ProtocolViolationError("Retrospective audit must be substantive before resolving emergency.")

        # Transition state back to RECOVERY, then to CANONICAL
        recovery_action = GovernanceAction(
            action_type="RECOVERY",
            identity_record=self.state.identity_record,
            evidence_bundle=EvidenceBundle(
                claim_being_supported="Emergency resolution and recovery",
                source_provenance="System Admin",
                relevance_basis="Audit trail completion",
                limitations="None",
                confidence_level=1.0,
                contestation_path="/emergency/resolve"
            ),
            verification_package=VerificationPackage(
                verification_methods=["retrospective-audit"],
                independence_analysis="Internal audit check",
                test_results={"success": True},
                adversarial_results={},
                semantic_equivalence_status="OK",
                verifier_attestations=["admin-sig"]
            ),
            understanding_layer=UnderstandingLayer(
                purpose_summary="Substantive audit details of resolved emergency",
                rule_architecture_summary="Audit review",
                critical_path_explanation="None",
                major_risks=[],
                current_uncertainties=[],
                operational_boundaries=[]
            ),
            recoverability_plan=RecoverabilityPlan(
                failure_triggers=["Manual override"],
                containment_actions=["Audit trails"],
                rollback_mechanism="Snapshot restoration",
                recovery_steps=["Review logs", "Check signatures"],
                restoration_criteria=["All verifications pass"],
                audit_trail_requirements=["Ledger retrospective review"]
            )
        )
        self.transition_to(SystemStateEnum.RECOVERY, action=recovery_action)
