from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

class SystemStateEnum(str, Enum):
    DRAFT = "DRAFT"
    PROVISIONAL = "PROVISIONAL"
    CANONICAL = "CANONICAL"
    CONTESTED = "CONTESTED"
    CONTAINED = "CONTAINED"
    RECOVERY = "RECOVERY"


class IdentityRecord(BaseModel):
    """
    Defines canonical state, lineage, continuity claim, preserved invariants,
    and unresolved continuity risks.
    """
    system_identifier: str = Field(..., description="Defines what the system is.")
    canonical_state_identifier: str = Field(..., description="What version/state it is in.")
    lineage_reference: str = Field(..., description="Continuous lineage reference/parent hash.")
    preserved_invariants: List[str] = Field(..., default_factory=list, description="List of preserved invariants.")
    declared_changes: List[str] = Field(..., default_factory=list, description="Declared changes or transitions.")
    unresolved_continuity_risks: List[str] = Field(..., default_factory=list, description="Unresolved continuity risks.")

    @field_validator("system_identifier", "canonical_state_identifier", "lineage_reference")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()


class EvidenceBundle(BaseModel):
    """
    Contains provenance, relevance basis, supporting records, confidence level,
    limitations, and contestation path.
    """
    claim_being_supported: str = Field(..., description="The claim being supported.")
    source_provenance: str = Field(..., description="Source provenance of the evidence.")
    relevance_basis: str = Field(..., description="Relevance basis of the evidence to the claim.")
    limitations: str = Field(..., description="Limitations of the evidence.")
    confidence_level: float = Field(..., description="Confidence level of the evidence, from 0.0 to 1.0.")
    contestation_path: str = Field(..., description="Contestation path details.")

    @field_validator("claim_being_supported", "source_provenance", "relevance_basis", "limitations", "contestation_path")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_level must be between 0.0 and 1.0")
        return v


class VerificationPackage(BaseModel):
    """
    Contains verification method, independence analysis, tests, adversarial checks,
    semantic equivalence status, and verifier attestations.
    """
    verification_methods: List[str] = Field(..., description="Verification methods used.")
    independence_analysis: str = Field(..., description="Analysis of the verifier's independence.")
    test_results: Dict[str, Any] = Field(..., description="Key-value mapping of test results.")
    adversarial_results: Dict[str, Any] = Field(..., description="Key-value mapping of adversarial checks.")
    semantic_equivalence_status: str = Field(..., description="Semantic equivalence status.")
    verifier_attestations: List[str] = Field(..., description="Verifier attestations or signatures.")

    @field_validator("independence_analysis", "semantic_equivalence_status")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()


class UnderstandingLayer(BaseModel):
    """
    Contains a human-auditable summary of purpose, structure, critical path,
    operational boundaries, and major risks.
    """
    purpose_summary: str = Field(..., description="Human-auditable summary of purpose.")
    rule_architecture_summary: str = Field(..., description="Summary of rule/architecture.")
    critical_path_explanation: str = Field(..., description="Explanation of the critical path.")
    major_risks: List[str] = Field(..., default_factory=list, description="Major identified risks.")
    current_uncertainties: List[str] = Field(..., default_factory=list, description="Current uncertainties.")
    operational_boundaries: List[str] = Field(..., default_factory=list, description="Operational boundaries or constraints.")

    @field_validator("purpose_summary", "rule_architecture_summary", "critical_path_explanation")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()


class RecoverabilityPlan(BaseModel):
    """
    Defines containment, rollback, repair, restoration, audit requirements,
    and reauthorization criteria.
    """
    failure_triggers: List[str] = Field(..., default_factory=list, description="Failure/dispute triggers.")
    containment_actions: List[str] = Field(..., default_factory=list, description="Actions for containment.")
    rollback_mechanism: str = Field(..., description="Mechanism used to rollback state.")
    recovery_steps: List[str] = Field(..., default_factory=list, description="Steps to recover system state.")
    restoration_criteria: List[str] = Field(..., default_factory=list, description="Criteria for successful restoration.")
    audit_trail_requirements: List[str] = Field(..., default_factory=list, description="Requirements for the audit trail.")

    @field_validator("rollback_mechanism")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()


class EvolutionPackage(BaseModel):
    """
    Required for any upgrade, migration, extension, configuration shift,
    or architectural change.
    """
    continuity_proof: str = Field(..., description="Proof of continuity between states.")
    preserved_invariants: List[str] = Field(..., default_factory=list, description="List of preserved invariants.")
    modified_invariants: List[str] = Field(..., default_factory=list, description="List of modified invariants.")
    removed_capabilities: List[str] = Field(..., default_factory=list, description="Capabilities removed in this version.")
    new_capabilities: List[str] = Field(..., default_factory=list, description="Capabilities introduced in this version.")
    second_order_impact_assessment: str = Field(..., description="Assessment of second-order impacts.")
    recovery_and_rollback_guarantees: str = Field(..., description="Guarantees for recovery/rollback.")
    independent_attestation: str = Field(..., description="Independent attestation of evolution.")

    @field_validator("continuity_proof", "second_order_impact_assessment", "recovery_and_rollback_guarantees", "independent_attestation")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only.")
        return v.strip()


class GovernanceAction(BaseModel):
    """
    Encapsulates a governance-relevant action along with the required
    complete set of artifacts as per the Enforcement Rule.
    """
    action_type: str = Field(..., description="Type of action (e.g. 'STANDARD', 'EVOLUTION')")
    identity_record: Optional[IdentityRecord] = Field(None, description="Identity Record artifact")
    evidence_bundle: Optional[EvidenceBundle] = Field(None, description="Evidence Bundle artifact")
    verification_package: Optional[VerificationPackage] = Field(None, description="Verification Package artifact")
    understanding_layer: Optional[UnderstandingLayer] = Field(None, description="Understanding Layer artifact")
    recoverability_plan: Optional[RecoverabilityPlan] = Field(None, description="Recoverability Plan artifact")
    evolution_package: Optional[EvolutionPackage] = Field(None, description="Evolution Package")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("STANDARD", "EVOLUTION", "PROPOSAL", "TRANSITION", "CONTESTATION", "DRIFT", "EMERGENCY", "RECOVERY"):
            raise ValueError(f"Invalid action_type: {v_upper}")
        return v_upper

    @model_validator(mode="after")
    def validate_dependency_order_and_enforcement(self) -> "GovernanceAction":
        # Check artifact dependency order (Dependency rule: cannot have higher without lower)
        # 1. Identity, 2. Evidence, 3. Verification, 4. Understanding, 5. Recoverability, 6. Evolution
        has_id = self.identity_record is not None
        has_ev = self.evidence_bundle is not None
        has_vp = self.verification_package is not None
        has_ul = self.understanding_layer is not None
        has_rp = self.recoverability_plan is not None
        has_ep = self.evolution_package is not None

        # Check in order: if we have N, we must have all N-1
        if has_ep and not has_rp:
            raise ValueError("Artifact dependency order violated: Evolution Package requires Recoverability Plan.")
        if has_rp and not has_ul:
            raise ValueError("Artifact dependency order violated: Recoverability Plan requires Understanding Layer.")
        if has_ul and not has_vp:
            raise ValueError("Artifact dependency order violated: Understanding Layer requires Verification Package.")
        if has_vp and not has_ev:
            raise ValueError("Artifact dependency order violated: Verification Package requires Evidence Bundle.")
        if has_ev and not has_id:
            raise ValueError("Artifact dependency order violated: Evidence Bundle requires Identity Record.")

        # Enforcement Rule: Standard action requires 1-5, Evolution requires 1-6
        if self.action_type in ("STANDARD", "EVOLUTION"):
            if not (has_id and has_ev and has_vp and has_ul and has_rp):
                raise ValueError(f"{self.action_type} action is non-canonical: incomplete minimal artifact set.")
            if self.action_type == "EVOLUTION" and not has_ep:
                raise ValueError("EVOLUTION action is non-canonical: missing Evolution Package.")

        return self


class SystemState(BaseModel):
    """
    Defines the canonical state of the system, including its identity record,
    associated active artifacts, runtime state, and metadata.
    """
    runtime_state: SystemStateEnum = Field(SystemStateEnum.DRAFT, description="Current runtime state of the system state machine.")
    identity_record: Optional[IdentityRecord] = Field(None, description="The current Identity Record of the system state.")
    last_evidence_bundle: Optional[EvidenceBundle] = Field(None, description="Last evidence bundle processed.")
    last_verification_package: Optional[VerificationPackage] = Field(None, description="Last verification package processed.")
    last_understanding_layer: Optional[UnderstandingLayer] = Field(None, description="Last understanding layer processed.")
    last_recoverability_plan: Optional[RecoverabilityPlan] = Field(None, description="Last recoverability plan processed.")
    last_evolution_package: Optional[EvolutionPackage] = Field(None, description="Last evolution package processed.")
    active_protocols: List[str] = Field(default_factory=list, description="Currently active protocols.")
    drift_metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics tracking potential system or verification drift.")
    trust_level: str = Field("HIGH", description="Current trust level of the system ('HIGH', 'DOWNGRADED').")
    is_emergency: bool = Field(False, description="Whether the system is currently in emergency/containment mode.")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Audit log of state transitions and events.")

    @property
    def is_canonical(self) -> bool:
        """Minimal Canonical Predicate"""
        has_all_required = (
            self.identity_record is not None and
            self.last_evidence_bundle is not None and
            self.last_verification_package is not None and
            self.last_understanding_layer is not None and
            self.last_recoverability_plan is not None
        )
        if self.last_evolution_package is not None:
            # For changes, must include evolution package
            return has_all_required
        return has_all_required
