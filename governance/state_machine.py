import datetime
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
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


@dataclass
class TransitionRule:
    source_states: Tuple[StatusEnum, ...]
    target_state: StatusEnum
    trigger: str
    required_predicates: List[Callable[[GovernanceObject], bool]] = field(default_factory=list)
    predicate_descriptions: List[str] = field(default_factory=list)
    forbidden_conditions: List[Callable[[GovernanceObject], bool]] = field(default_factory=list)
    forbidden_descriptions: List[str] = field(default_factory=list)
    ledger_effect: List[str] = field(default_factory=list)
    rollback_path: str = "none"


TRANSITION_TABLE: List[TransitionRule] = [
    TransitionRule(
        source_states=(StatusEnum.DRAFT,),
        target_state=StatusEnum.PROVISIONAL,
        trigger="Minimal staging of evidence-backed proposal",
        required_predicates=[
            lambda o: bool(o.provenance),
            lambda o: o.evidence_bundle is not None,
            lambda o: o.understanding_layer is not None and bool(o.understanding_layer.operational_boundaries)
        ],
        predicate_descriptions=[
            "minimal provenance.",
            "initial evidence.",
            "initial scope declaration."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition", "evidence_reference"],
        rollback_path="Discard draft proposal"
    ),
    TransitionRule(
        source_states=(StatusEnum.PROVISIONAL,),
        target_state=StatusEnum.CANONICAL,
        trigger="Complete verification and independent review signoff",
        required_predicates=[
            lambda o: (o.evidence_bundle is not None and o.verification_package is not None and
                       o.understanding_layer is not None and o.recoverability_plan is not None),
            lambda o: bool(o.signatures),
            lambda o: o.verification_package is not None and o.verification_package.semantic_equivalence_status == "IDENTICAL"
        ],
        predicate_descriptions=[
            "all 4 standard artifacts.",
            "explicit activation signatures.",
            "semantic equivalence validation."
        ],
        forbidden_conditions=[
            lambda o: o.contestation_state != "uncontested"
        ],
        forbidden_descriptions=[
            "Cannot transition if the object is actively contested."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition", "evidence_reference", "verifier_reference", "rollback_reference"],
        rollback_path="Standard rollback defined in RecoverabilityPlan"
    ),
    TransitionRule(
        source_states=(StatusEnum.CANONICAL,),
        target_state=StatusEnum.CONTESTED,
        trigger="Valid challenge registration against canonical state",
        required_predicates=[
            lambda o: o.contestation_state != "uncontested"
        ],
        predicate_descriptions=[
            "active contestation state registration."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition", "contestation_reference"],
        rollback_path="Provisional containment or dispute resolution"
    ),
    TransitionRule(
        source_states=(StatusEnum.CANONICAL, StatusEnum.PROVISIONAL),
        target_state=StatusEnum.CONTAINED,
        trigger="System drift, verification mismatch, or compromise detected",
        required_predicates=[],
        ledger_effect=["previous_status", "new_status", "reason_for_transition"],
        rollback_path="Activation of ContainmentActions"
    ),
    TransitionRule(
        source_states=(StatusEnum.CONTAINED,),
        target_state=StatusEnum.RECOVERY,
        trigger="Containment acknowledgment and audit repair kickoff",
        required_predicates=[
            lambda o: o.recoverability_plan is not None and bool(o.recoverability_plan.recovery_steps)
        ],
        predicate_descriptions=[
            "restoration plan and recovery steps."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition", "rollback_reference"],
        rollback_path="Rollback tool repair path"
    ),
    TransitionRule(
        source_states=(StatusEnum.RECOVERY,),
        target_state=StatusEnum.CANONICAL,
        trigger="Successful repair validation and independent reauthorization",
        required_predicates=[
            lambda o: o.verification_package is not None and o.evolution_package is not None,
            lambda o: bool(o.signatures)
        ],
        predicate_descriptions=[
            "validation package and evolution proof.",
            "independent reauthorization signatures."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition", "verifier_reference"],
        rollback_path="Full system rollback"
    ),
    TransitionRule(
        source_states=(StatusEnum.CANONICAL,),
        target_state=StatusEnum.DEPRECATED,
        trigger="Retirement of component after reassessment",
        required_predicates=[
            lambda o: "deprecated" in o.timestamps
        ],
        predicate_descriptions=[
            "deprecated timestamp in object's timestamps."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition"],
        rollback_path="None (terminal or replacement path)"
    ),
    TransitionRule(
        source_states=(StatusEnum.CANONICAL,),
        target_state=StatusEnum.REVOKED,
        trigger="Decisive invalidation due to compromise",
        required_predicates=[
            lambda o: "revoked" in o.timestamps
        ],
        predicate_descriptions=[
            "revoked timestamp in object's timestamps."
        ],
        ledger_effect=["previous_status", "new_status", "reason_for_transition"],
        rollback_path="Immediate successor state transition"
    )
]


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
        Enforces Section 3: Transition Table rules, Integrity Predicates,
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
            for field_name, val in action_obj.model_dump(exclude_unset=True).items():
                if val is not None:
                    new_obj_data[field_name] = val

        # Ensure version increments for state updates/transitions
        new_obj_data["version"] = current_obj.version + 1
        new_obj_data["parent_reference"] = current_obj.object_id

        # Before instantiating, set deprecated/revoked timestamps if transitioning to those states
        if target_status == StatusEnum.DEPRECATED and "deprecated" not in new_obj_data.get("timestamps", {}):
            new_obj_data.setdefault("timestamps", {})["deprecated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        elif target_status == StatusEnum.REVOKED and "revoked" not in new_obj_data.get("timestamps", {}):
            new_obj_data.setdefault("timestamps", {})["revoked"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Instantiate target object and validate schema/dependency rules
        try:
            target_obj = GovernanceObject(**new_obj_data)
        except ValidationError as e:
            raise ProtocolViolationError(f"Validation Error during transition instantiation: {e}")

        # Find matching transition rule in Transition Table
        rule = None
        for r in TRANSITION_TABLE:
            if current_status in r.source_states and r.target_state == target_status:
                rule = r
                break

        if not rule:
            raise ProtocolViolationError(f"Direct transition from {current_status} to {target_status} is invalid under Transition Contract.")

        # Evaluate required predicates
        for pred, desc in zip(rule.required_predicates, rule.predicate_descriptions):
            if not pred(target_obj):
                raise ProtocolViolationError(f"{current_status.value.capitalize()} -> {target_status.value.capitalize()} requires {desc}")

        # Evaluate forbidden conditions
        for cond, desc in zip(rule.forbidden_conditions, rule.forbidden_descriptions):
            if cond(target_obj):
                raise ProtocolViolationError(f"Transition block: {desc}")

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
