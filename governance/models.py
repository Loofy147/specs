from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

class ObjectTypeEnum(str, Enum):
    IDENTITY_RECORD = "identity_record"
    EVIDENCE_BUNDLE = "evidence_bundle"
    VERIFICATION_PACKAGE = "verification_package"
    UNDERSTANDING_LAYER = "understanding_layer"
    RECOVERABILITY_PLAN = "recoverability_plan"
    EVOLUTION_PACKAGE = "evolution_package"
    STATE_TRANSITION = "state_transition"
    CHALLENGE_RECORD = "challenge_record"
    AUDIT_RECORD = "audit_record"
    AUTHORITY_RECORD = "authority_record"


class StatusEnum(str, Enum):
    DRAFT = "draft"
    PROVISIONAL = "provisional"
    CANONICAL = "canonical"
    CONTESTED = "contested"
    CONTAINED = "contained"
    RECOVERY = "recovery"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


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


class UnderstandingWitness(BaseModel):
    """
    A formal structural witness proving human-auditable comprehension.
    This is an auditable comprehension record, NOT a cryptographic proof.
    """
    purpose_summary: str = Field(..., description="Auditable description of purpose.")
    dependency_path: List[str] = Field(..., description="Verification/dependency paths.")
    critical_path_explanation: str = Field(..., description="Explanation of critical paths.")
    reviewer_signature: str = Field(..., description="Signature of the human reviewer.")
    checklist: Dict[str, bool] = Field(..., description="Bounded checklist of understood components.")


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
    understanding_witness: Optional[UnderstandingWitness] = Field(None, description="Auditable structural witness comprehension record.")

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


class GovernanceObject(BaseModel):
    """
    Representing the Canonical Object Schema that wraps all governance objects.
    """
    object_id: str = Field(..., description="Globally unique immutable identifier.")
    object_type: ObjectTypeEnum = Field(..., description="Type of the governance object.")
    status: StatusEnum = Field(..., description="Status of the object in the runtime model.")
    version: int = Field(..., description="Monotonic version label for the object.")
    parent_reference: str = Field(..., description="Reference to the prior object or state from which this derives.")
    provenance: str = Field(..., description="Source chain, origin context, and creation path.")
    evidence_bundle: Optional[EvidenceBundle] = Field(None, description="Traceable support for the object claim.")
    verification_package: Optional[VerificationPackage] = Field(None, description="Independent validation results.")
    understanding_layer: Optional[UnderstandingLayer] = Field(None, description="Human-auditable explanation of purpose.")
    recoverability_plan: Optional[RecoverabilityPlan] = Field(None, description="Rollback and restoration instructions.")
    evolution_package: Optional[EvolutionPackage] = Field(None, description="Present if change is involved.")
    contestation_state: str = Field("uncontested", description="Current challenge status ('uncontested' or challenge IDs).")
    trust_tier: str = Field("standard", description="Current authority class or confidence class.")
    timestamps: Dict[str, str] = Field(default_factory=dict, description="Creation, validation, activation, review, and expiry timestamps.")
    signatures: List[str] = Field(default_factory=list, description="Cryptographic or attestational signatures required for authority.")

    @field_validator("object_id", "parent_reference", "provenance")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty.")
        return v.strip()

    @model_validator(mode="after")
    def validate_dependency_order_and_canonical_rules(self) -> "GovernanceObject":
        has_ev = self.evidence_bundle is not None
        has_vp = self.verification_package is not None
        has_ul = self.understanding_layer is not None
        has_rp = self.recoverability_plan is not None
        has_ep = self.evolution_package is not None

        # Dependency order rules (Identity -> Evidence -> Verification -> Understanding -> Recoverability -> Evolution)
        if has_ep and not has_rp:
            raise ValueError("Artifact dependency order violated: Evolution Package requires Recoverability Plan.")
        if has_rp and not has_ul:
            raise ValueError("Artifact dependency order violated: Recoverability Plan requires Understanding Layer.")
        if has_ul and not has_vp:
            # For draft or provisional state, we might have evidence_bundle and understanding_layer without verification_package
            if self.status == StatusEnum.CANONICAL:
                raise ValueError("Artifact dependency order violated: Understanding Layer requires Verification Package.")
        if has_vp and not has_ev:
            raise ValueError("Artifact dependency order violated: Verification Package requires Evidence Bundle.")

        # Canonicalization Rule / Integrity Predicate (Section 5, 6)
        if self.status == StatusEnum.CANONICAL:
            if not (has_ev and has_vp and has_ul and has_rp):
                raise ValueError("Canonicalization Rule Violated: Incomplete required standard artifacts.")
            if not self.timestamps.get("creation") or not self.timestamps.get("activation"):
                raise ValueError("Canonicalization Rule Violated: Timestamps (creation, activation) must be present.")
            if not self.signatures:
                raise ValueError("Canonicalization Rule Violated: Active authority signatures required.")
            if self.contestation_state != "uncontested":
                raise ValueError("Canonicalization Rule Violated: Object is under active contestation.")

        return self


class LedgerEntry(BaseModel):
    """
    Ledger Requirement: Representing an immutable ledger trace of a status transition.
    """
    previous_status: StatusEnum = Field(..., description="Previous state status.")
    new_status: StatusEnum = Field(..., description="New state status.")
    reason_for_transition: str = Field(..., description="Rationale/reason for the transition.")
    evidence_reference: str = Field(..., description="Trace reference to the evidence backing transition.")
    verifier_reference: str = Field(..., description="Verifier attestation/package reference.")
    contestation_reference: Optional[str] = Field(None, description="Reference to contestation record if applicable.")
    rollback_reference: str = Field(..., description="Rollback path reference.")
    timestamp: str = Field(..., description="ISO UTC timestamp of the ledger record.")
    signer_identity: str = Field(..., description="Identity of the authority signing the transition.")


class GovernanceAction(BaseModel):
    """
    Encapsulates a governance action that executes on a GovernanceObject.
    """
    action_type: str = Field(..., description="Type of action (e.g. 'DRAFT_TO_PROVISIONAL', 'PROVISIONAL_TO_CANONICAL', etc.)")
    target_object: GovernanceObject = Field(..., description="The governance object to be processed or transitioned.")


class SystemState(BaseModel):
    """
    Defines the canonical state of the system, including its current active
    GovernanceObject, ledger history, drift metrics, and active protocols.
    """
    current_object: GovernanceObject = Field(..., description="The current active GovernanceObject representing system state.")
    ledger: List[LedgerEntry] = Field(default_factory=list, description="Immutable ledger of state status transitions.")
    active_protocols: List[str] = Field(default_factory=list, description="Currently active protocols.")
    drift_metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics tracking system or verification drift.")
    trust_level: str = Field("HIGH", description="Current trust level of the system ('HIGH', 'DOWNGRADED').")
    is_emergency: bool = Field(False, description="Whether the system is in containment/emergency mode.")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="General audit log of state operations.")
