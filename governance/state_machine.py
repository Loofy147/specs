from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from governance.models import (
    SystemState, GovernanceAction, IdentityRecord, EvidenceBundle,
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
    Enforces the Master Governance Constitution and manages system state transitions,
    governing protocols, and authority checks.
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
        Authority is valid only when:
        - declared,
        - attested,
        - traceable,
        - independently reviewable,
        - subject to contestation,
        - expires or is renewed according to policy.
        """
        # Ensure verifier attestations exist
        if not action.verification_package.verifier_attestations:
            return False
        # Ensure source provenance is declared
        if not action.evidence_bundle.source_provenance:
            return False
        # Ensure there is a contestation path
        if not action.evidence_bundle.contestation_path:
            return False
        return True

    def transition(self, action: GovernanceAction) -> SystemState:
        """
        Enforces Section 4.1 (Canonicalization Protocol) and Section 6 (Transition Rules):
        Transitions the state machine to a new state based on a valid GovernanceAction.
        """
        # 1. Enforcement Rule (checked by Pydantic model validation on Action structure, but double checked here)
        if action.action_type == "EVOLUTION" and not action.evolution_package:
            raise InvariantViolationError("Evolution Package is missing for an EVOLUTION action.")

        # 2. Check Identity/Continuity constraint (Section 2.1 & Section 6)
        # The transition's lineage reference must point to the current state's canonical state identifier
        if action.identity_record.lineage_reference != self.state.identity_record.canonical_state_identifier:
            raise InvariantViolationError(
                f"Lineage break: action lineage reference '{action.identity_record.lineage_reference}' "
                f"does not match current state identifier '{self.state.identity_record.canonical_state_identifier}'."
            )

        # 3. Check System Identifier continuity
        if action.identity_record.system_identifier != self.state.identity_record.system_identifier:
            raise InvariantViolationError(
                f"System mismatch: action system '{action.identity_record.system_identifier}' "
                f"does not match current system '{self.state.identity_record.system_identifier}'."
            )

        # 4. Authority verification (Section 5)
        if not self._verify_authority(action):
            raise ProtocolViolationError("Authority rules check failed (Section 5 violation).")

        # 5. Evidence check (Section 2.2)
        if action.evidence_bundle.confidence_level < 0.5:
            raise ProtocolViolationError(
                f"Evidence confidence level too low: {action.evidence_bundle.confidence_level}. "
                "Minimum confidence is 0.5."
            )

        # 6. Verification Package Checks (Section 2.3)
        # Ensure there is at least one verification method and one verifier attestation
        if not action.verification_package.verification_methods:
            raise ProtocolViolationError("No verification methods declared.")

        # Verify test results do not indicate a critical failure (e.g., any failure count > 0)
        test_results = action.verification_package.test_results
        if test_results.get("failed", 0) > 0 or test_results.get("success") is False:
            raise ProtocolViolationError("Verification package test results contain failures.")

        # 7. Understandability (Section 2.4 & Section 8)
        # Ensure description fields are non-trivial
        if len(action.understanding_layer.purpose_summary) < 10:
            raise ProtocolViolationError("Understanding layer purpose summary is too brief to be human-auditable.")

        # 8. Recoverability Plan (Section 2.5)
        if not action.recoverability_plan.rollback_mechanism:
            raise ProtocolViolationError("Recoverability plan lacks a defined rollback mechanism.")

        # 9. If EVOLUTION action, enforce upgrade criteria
        if action.action_type == "EVOLUTION" and action.evolution_package:
            # Check upgrade control stages if we had a proposal in flight
            if self._upgrade_proposal:
                if self._upgrade_proposal["stage"] != "MONITORING":
                    raise ProtocolViolationError(
                        f"Cannot commit upgrade. Current stage is '{self._upgrade_proposal['stage']}', "
                        "must be 'MONITORING' before committing."
                    )
                # Clear proposal as it's now committed
                self._upgrade_proposal = None

            # Evolution specific checks
            evo = action.evolution_package
            if not evo.continuity_proof:
                raise InvariantViolationError("Evolution package requires a continuity proof.")

        # Record state transition in history
        timestamp = datetime.now(timezone.utc).isoformat()
        history_entry = {
            "timestamp": timestamp,
            "previous_state_id": self.state.identity_record.canonical_state_identifier,
            "new_state_id": action.identity_record.canonical_state_identifier,
            "action_type": action.action_type,
            "system_identifier": action.identity_record.system_identifier
        }

        # Build new SystemState
        new_state = SystemState(
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

    def challenge_artifact(self, target_artifact: str, basis: str, evidence: str, burden_of_proof: str) -> Dict[str, Any]:
        """
        Enforces Section 4.2 (Contestation Protocol):
        Any canonical artifact may be challenged through a bounded and auditable process.
        """
        if not target_artifact or not basis or not evidence or not burden_of_proof:
            raise ProtocolViolationError("Contestation requires target_artifact, basis, evidence, and burden_of_proof.")

        # Provisional safety action: downgrade trust on serious challenge
        self.state.trust_level = "DOWNGRADED"

        outcome = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_artifact": target_artifact,
            "basis": basis,
            "evidence": evidence,
            "burden_of_proof": burden_of_proof,
            "provisional_status": "CHALLENGED",
            "action_taken": "Trust level downgraded to DOWNGRADED. System enters review."
        }

        self.state.history.append({
            "event": "CONTESTATION_FILED",
            "timestamp": outcome["timestamp"],
            "target": target_artifact,
            "outcome": outcome
        })

        return outcome

    def evaluate_recursive_process(self, current_depth: int, max_depth: int) -> bool:
        """
        Enforces Section 4.3 (Recursion Control Protocol):
        Any self-referential or meta-level process must declare a finite recursion depth.
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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

        # Enforce progressive staging
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
        If measurement systems, thresholds, or verification tools drift,
        the system must downgrade trust, contain impact, and record the trace.
        """
        self.state.drift_metrics[metric_name] = {
            "value": value,
            "threshold": threshold,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if value > threshold:
            self.state.trust_level = "DOWNGRADED"
            self.state.history.append({
                "event": "DRIFT_DETECTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metric_name": metric_name,
                "value": value,
                "threshold": threshold,
                "action": "Downgraded trust level due to metric drift."
            })

    def declare_emergency(self, trigger: str, scope: str, duration_hours: int):
        """
        Enforces Section 4.7 (Containment and Emergency Protocol):
        Emergency actions are permitted only under declared triggers, bounded scope,
        time limits, and retrospective contestation.
        """
        if not trigger or not scope or duration_hours <= 0:
            raise ProtocolViolationError("Emergency declaration requires a trigger, scope, and positive duration limit.")

        self.state.is_emergency = True
        self.state.history.append({
            "event": "EMERGENCY_DECLARED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "scope": scope,
            "duration_hours": duration_hours
        })

    def resolve_emergency(self, retrospective_review: str):
        """Resolves emergency mode after performing an obligatory retrospective audit."""
        if not self.state.is_emergency:
            raise ProtocolViolationError("System is not currently in emergency mode.")

        if len(retrospective_review) < 15:
            raise ProtocolViolationError("Retrospective audit must be substantive before resolving emergency.")

        self.state.is_emergency = False
        self.state.history.append({
            "event": "EMERGENCY_RESOLVED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retrospective_review": retrospective_review
        })
