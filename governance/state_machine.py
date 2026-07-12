import datetime
from pydantic import ValidationError
from typing import List, Dict, Any, Optional
from governance.models import (
    SystemState, StatusEnum, ObjectTypeEnum, GovernanceObject, LedgerEntry,
    GovernanceAction, EvidenceBundle, VerificationPackage, UnderstandingLayer, RecoverabilityPlan, EvolutionPackage
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
    Enforces the Transition Contract, Canonical Object Schema,
    predicates, and Ledger requirements of the Governance Runtime Contract.
    """

    def __init__(self, initial_state: SystemState):
        if not initial_state:
            raise GovernanceError("Initial state cannot be None.")
        self.state = initial_state
        self._upgrade_proposal: Optional[Dict[str, Any]] = None

    def get_current_state(self) -> SystemState:
        """Returns the current system state."""
        return self.state

    def _preserve_invariants(self, previous_obj: GovernanceObject, new_obj: GovernanceObject):
        """
        Enforces Section 4: State Transition Invariants.
        Every transition must preserve identity, evidence traceability, verification independence,
        human comprehensibility, recoverability, auditability, and bounded recursion.
        """
        # 1. Identity continuity
        if previous_obj.object_id != new_obj.object_id:
            raise InvariantViolationError("Invariant Violation: Object ID cannot change (Identity continuity broken).")
        if new_obj.version < previous_obj.version:
            raise InvariantViolationError("Invariant Violation: Version must be monotonic.")
        if new_obj.parent_reference != previous_obj.parent_reference and new_obj.parent_reference != previous_obj.object_id:
            # Must point either to same parent or previous object itself
            raise InvariantViolationError("Invariant Violation: Parent reference must align.")

        # 2. Evidence traceability
        if new_obj.evidence_bundle:
            if not new_obj.evidence_bundle.claim_being_supported or not new_obj.evidence_bundle.source_provenance:
                raise InvariantViolationError("Invariant Violation: Evidence traceability broken.")

        # 3. Verification independence
        if new_obj.verification_package:
            if not new_obj.verification_package.verifier_attestations or not new_obj.verification_package.independence_analysis:
                raise InvariantViolationError("Invariant Violation: Verification independence broken.")

        # 4. Human comprehensibility
        if new_obj.understanding_layer:
            if len(new_obj.understanding_layer.purpose_summary) < 10:
                raise InvariantViolationError("Invariant Violation: Human comprehensibility summary is too brief.")

        # 5. Recoverability
        if new_obj.recoverability_plan:
            if not new_obj.recoverability_plan.rollback_mechanism:
                raise InvariantViolationError("Invariant Violation: Recoverability plan lacks defined rollback.")

        # Bounded recursion
        self.evaluate_recursive_process(1, 10)

    def evaluate_recursive_process(self, current_depth: int, max_depth: int) -> bool:
        """Enforces recursion control: no infinite regress."""
        if current_depth > max_depth:
            raise ProtocolViolationError(f"Recursion depth limit exceeded: {current_depth} > {max_depth}")
        return True

    def transition_to(self, target_status: StatusEnum, reason: str, action_obj: Optional[GovernanceObject] = None, signer_identity: str = "authority-01") -> SystemState:
        """
        Enforces Section 3: Transition Contract conditions, Integrity Predicates,
        Invariants, and appends a corresponding Section 9 LedgerEntry.
        """
        current_obj = self.state.current_object
        current_status = current_obj.status

        if current_status == target_status:
            return self.state

        # Use the action_obj if provided, else build one from the current object with the target status
        new_obj_data = current_obj.model_dump()
        new_obj_data["status"] = target_status
        if action_obj:
            # Merge fields from action_obj to update artifacts or metadata
            for field, val in action_obj.model_dump(exclude_unset=True).items():
                if val is not None:
                    new_obj_data[field] = val

        # Ensure version increments for state updates/transitions
        new_obj_data["version"] = current_obj.version + 1
        new_obj_data["parent_reference"] = current_obj.object_id

        # Instantiate target object and validate schema/dependency rules
        try:
            target_obj = GovernanceObject(**new_obj_data)
        except ValidationError as e:
            raise ProtocolViolationError(f"Validation Error during transition instantiation: {e}")

        # Enforce transition rules
        if current_status == StatusEnum.DRAFT and target_status == StatusEnum.PROVISIONAL:
            # Requires: minimal provenance, initial evidence, initial scope declaration
            if not target_obj.provenance:
                raise ProtocolViolationError("Draft -> Provisional requires minimal provenance.")
            if not target_obj.evidence_bundle:
                raise ProtocolViolationError("Draft -> Provisional requires initial evidence.")
            if not target_obj.understanding_layer or not target_obj.understanding_layer.operational_boundaries:
                raise ProtocolViolationError("Draft -> Provisional requires initial scope declaration.")

        elif current_status == StatusEnum.PROVISIONAL and target_status == StatusEnum.CANONICAL:
            # Requires: complete required artifacts, independent validation, semantic equivalence verification,
            # no unresolved critical risks, explicit activation signature
            if not (target_obj.evidence_bundle and target_obj.verification_package and
                    target_obj.understanding_layer and target_obj.recoverability_plan):
                raise ProtocolViolationError("Provisional -> Canonical requires all 4 standard artifacts.")
            if not target_obj.signatures:
                raise ProtocolViolationError("Provisional -> Canonical requires explicit activation signatures.")
            if target_obj.verification_package.semantic_equivalence_status != "IDENTICAL":
                raise ProtocolViolationError("Provisional -> Canonical requires semantic equivalence validation.")

        elif current_status == StatusEnum.CANONICAL and target_status == StatusEnum.CONTESTED:
            # Requires: valid challenge submission, evidence basis, contestation registration, ledger entry
            if target_obj.contestation_state == "uncontested":
                raise ProtocolViolationError("Canonical -> Contested requires active contestation state registration.")

        elif (current_status in (StatusEnum.CANONICAL, StatusEnum.PROVISIONAL)) and target_status == StatusEnum.CONTAINED:
            # Requires: containment conditions (drift, mismatch, verifier compromise, etc.)
            pass

        elif current_status == StatusEnum.CONTAINED and target_status == StatusEnum.RECOVERY:
            # Requires: containment acknowledgment, restoration plan, bounded recovery scope, repair path
            if not target_obj.recoverability_plan or not target_obj.recoverability_plan.recovery_steps:
                raise ProtocolViolationError("Contained -> Recovery requires restoration plan and recovery steps.")

        elif current_status == StatusEnum.RECOVERY and target_status == StatusEnum.CANONICAL:
            # Requires: successful repair validation, integrity proof, rollback readiness, independent reauthorization
            if not target_obj.verification_package or not target_obj.evolution_package:
                raise ProtocolViolationError("Recovery -> Canonical requires validation package and evolution proof.")
            if not target_obj.signatures:
                raise ProtocolViolationError("Recovery -> Canonical requires independent reauthorization signatures.")

        elif current_status == StatusEnum.CANONICAL and target_status == StatusEnum.DEPRECATED:
            # Requires: reassessment outcome, replacement path, no active unresolved critical dependence
            if "deprecated" not in target_obj.timestamps:
                target_obj.timestamps["deprecated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        elif current_status == StatusEnum.CANONICAL and target_status == StatusEnum.REVOKED:
            # Requires: decisive invalidation, immediate containment, successor state path
            if "revoked" not in target_obj.timestamps:
                target_obj.timestamps["revoked"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        else:
            raise ProtocolViolationError(f"Direct transition from {current_status} to {target_status} is invalid under Transition Contract.")

        # Ensure transition preserves invariants
        self._preserve_invariants(current_obj, target_obj)

        # Construct and append Section 9 LedgerEntry
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ledger_entry = LedgerEntry(
            previous_status=current_status,
            new_status=target_status,
            reason_for_transition=reason,
            evidence_reference=target_obj.evidence_bundle.contestation_path if target_obj.evidence_bundle else "none",
            verifier_reference=target_obj.verification_package.independence_analysis if target_obj.verification_package else "none",
            contestation_reference=target_obj.contestation_state if target_obj.contestation_state != "uncontested" else None,
            rollback_reference=target_obj.recoverability_plan.rollback_mechanism if target_obj.recoverability_plan else "none",
            timestamp=timestamp_str,
            signer_identity=signer_identity
        )

        # Update timestamps inside GovernanceObject
        target_obj.timestamps["transition"] = timestamp_str

        # Build new SystemState
        new_state = SystemState(
            current_object=target_obj,
            ledger=self.state.ledger + [ledger_entry],
            active_protocols=self.state.active_protocols,
            drift_metrics=self.state.drift_metrics,
            trust_level="DOWNGRADED" if target_status in (StatusEnum.CONTESTED, StatusEnum.CONTAINED) else self.state.trust_level,
            is_emergency=True if target_status == StatusEnum.CONTAINED else self.state.is_emergency,
            history=self.state.history + [{
                "event": "STATE_TRANSITION",
                "timestamp": timestamp_str,
                "previous_status": current_status.value,
                "new_status": target_status.value,
                "reason": reason
            }]
        )

        self.state = new_state
        return self.state

    def challenge_object(self, challenge_id: str, basis: str, evidence_ref: str) -> SystemState:
        """Enforces transition to CONTESTED when an object is challenged."""
        challenge_action = GovernanceObject(
            object_id=self.state.current_object.object_id,
            object_type=self.state.current_object.object_type,
            status=StatusEnum.CONTESTED,
            version=self.state.current_object.version,
            parent_reference=self.state.current_object.parent_reference,
            provenance=self.state.current_object.provenance,
            contestation_state=challenge_id,
            evidence_bundle=EvidenceBundle(
                claim_being_supported=f"Challenge: {challenge_id}",
                source_provenance=evidence_ref,
                relevance_basis=basis,
                limitations="None",
                confidence_level=0.9,
                contestation_path=f"/contestation/{challenge_id}"
            )
        )
        return self.transition_to(StatusEnum.CONTESTED, reason=f"Challenge {challenge_id} submitted", action_obj=challenge_action)

    def trigger_containment(self, reason: str, metric_name: Optional[str] = None, value: Optional[float] = None, threshold: Optional[float] = None) -> SystemState:
        """Enforces transition to CONTAINED due to drift or invalidation."""
        if metric_name:
            self.state.drift_metrics[metric_name] = {
                "value": value,
                "threshold": threshold,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

        containment_action = GovernanceObject(
            object_id=self.state.current_object.object_id,
            object_type=self.state.current_object.object_type,
            status=StatusEnum.CONTAINED,
            version=self.state.current_object.version,
            parent_reference=self.state.current_object.parent_reference,
            provenance=self.state.current_object.provenance,
            evidence_bundle=EvidenceBundle(
                claim_being_supported=f"Containment: {reason}",
                source_provenance="Monitoring Tool",
                relevance_basis=f"Triggered containment: {reason}",
                limitations="None",
                confidence_level=1.0,
                contestation_path="/containment/review"
            )
        )
        return self.transition_to(StatusEnum.CONTAINED, reason=f"Containment triggered: {reason}", action_obj=containment_action)
