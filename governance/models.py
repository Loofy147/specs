from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

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
    identity_record: IdentityRecord = Field(..., description="Identity Record artifact")
    evidence_bundle: EvidenceBundle = Field(..., description="Evidence Bundle artifact")
    verification_package: VerificationPackage = Field(..., description="Verification Package artifact")
    understanding_layer: UnderstandingLayer = Field(..., description="Understanding Layer artifact")
    recoverability_plan: RecoverabilityPlan = Field(..., description="Recoverability Plan artifact")
    evolution_package: Optional[EvolutionPackage] = Field(None, description="Evolution Package (required only for EVOLUTION actions)")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("STANDARD", "EVOLUTION"):
            raise ValueError("action_type must be either 'STANDARD' or 'EVOLUTION'.")
        return v_upper

    @model_validator(mode="after")
    def validate_enforcement_rule(self) -> "GovernanceAction":
        if self.action_type == "EVOLUTION" and self.evolution_package is None:
            raise ValueError("Evolution Package is required for EVOLUTION actions (Enforcement Rule).")
        return self


class SystemState(BaseModel):
    """
    Defines the canonical state of the system, including its identity record,
    associated active artifacts, and metadata.
    """
    identity_record: IdentityRecord = Field(..., description="The current Identity Record of the system state.")
    last_evidence_bundle: Optional[EvidenceBundle] = Field(None, description="Last evidence bundle processed.")
    last_verification_package: Optional[VerificationPackage] = Field(None, description="Last verification package processed.")
    last_understanding_layer: Optional[UnderstandingLayer] = Field(None, description="Last understanding layer processed.")
    last_recoverability_plan: Optional[RecoverabilityPlan] = Field(None, description="Last recoverability plan processed.")
    last_evolution_package: Optional[EvolutionPackage] = Field(None, description="Last evolution package processed if latest was evolution.")
    active_protocols: List[str] = Field(default_factory=list, description="Currently active protocols.")
    drift_metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics tracking potential system or verification drift.")
    trust_level: str = Field("HIGH", description="Current trust level of the system ('HIGH', 'DOWNGRADED').")
    is_emergency: bool = Field(False, description="Whether the system is currently in emergency/containment mode.")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Audit log of state transitions.")
