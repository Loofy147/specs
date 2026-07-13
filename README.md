# Sovereign Governance Constitution System

A compact, highly robust, machine-verifiable, and human-auditable framework for sovereign governance. This repository implements formal state machine transitions, strict atomic schema validation, genuine public-key cryptography (Ed25519 PKI), bounded recursion engines, and mathematical SMT-proven theorems to enforce core system invariants across all governance transitions and releases.

---

## 🗺️ Completed Milestones & Roadmap Checkouts

1. **Strict Atomic Schema Verification & Gatekeeping (`kernel.py` / `governance_kernel.py`)**
   - Established a rigid `ALLOWED_CHECK_KEYS` gatekeeper.
   - Any misspelled, unknown, or undeclared atomic predicate key on construction or access immediately raises a fast-failing `KeyError`.
2. **Promoted Understanding Witnessing (`atomic_engines.py` & `governance/models.py`)**
   - Promoted the raw `Understandable` boolean predicate into an evidence-backed structure called `UnderstandingWitness`.
   - Explicitly checks word counts, dependency paths, critical path explanations, and reviewer signatures.
   - Built-in explicit in-code disclaimer stating this represents a structural compliance proxy, not a cognitive/cryptographic proof.
3. **Formal State Machine & Declarative Transition Table (`governance/state_machine.py`)**
   - Implemented a complete `TRANSITION_TABLE` defining allowed source $\to$ target state transitions.
   - Enforces strict execution preconditions, forbidden states (e.g. active contestations blocking canonical transitions), detailed ledger effect fields, and precise rollback paths.
4. **8 Canonical SMT Theorems (`smt_theorems.py`)**
   - Expanded theorem proving from 4 to 8 theorems using the Z3 SMT solver.
   - Proves math properties over infinite domains (metric alignment, trust-decay clamp monotonicity).
   - Proves unbounded history inductive invariants (version monotonicity and append-only ledger preservation) via Z3 array theory.
   - Proves a BMC-style existence check that a `CONTAINED` $\to$ `RECOVERY` $\to$ `CANONICAL` path always exists under valid evidence.
5. **Real Cryptographic Release Manifest Freezing (`freeze_manifest.py`)**
   - Replaced simulated/mock signatures with genuine Ed25519 keypair generation and signing using standard primitives from the `cryptography` package.
   - Generates a signed, self-contained `release_manifest.json` locking in SHA-256 hashes of all critical files (`governance_math.tex`, `kernel.py`, `atomic_engines.py`, `smt_theorems.py`, `pki.py`).
6. **Robust Dual-Mode Release Verification (`verify_manifest.py`)**
   - Implemented separate, distinct verification steps for **Signature Tampering** and **On-Disk Content Drift**.
   - Supports specific diagnostics reporting which file or signature has drifted or been tampered with.

---

## 📁 Repository Directory Structure

```
├── governance/                   # Pydantic v2 domain model layer & state machine
│   ├── models.py                 # Core Pydantic schemas for artifacts & states
│   └── state_machine.py          # Transition Contract & Transition Table engine
├── schemas/                      # Auto-generated JSON Schemas for canonical artifacts
├── tests/                        # Repository test suites
│   └── test_governance.py        # Pydantic schema validation & state transition tests
├── README.md                     # Project documentation, checklists, and roadmap
├── atomic_engines.py             # Concrete evaluation engines for atomic predicates
├── freeze_manifest.py            # Ed25519-based release manifest generation script
├── verify_manifest.py            # Dual-mode cryptographic & drift validation engine
├── kernel.py                     # Boolean algebra core implementing constitution logics
├── governance_kernel.py          # Duplicate/alias of kernel.py for import stability
├── pki.py                        # Standard Ed25519 PKI and SHA-256 hash chaining module
├── smt_theorems.py               # Z3 solver theorem proving script (8 proved theorems)
├── run_scenarios.py              # Empirical scenario validation script (53 scenario checks)
├── release_manifest.json         # Canonical frozen release manifest
└── specs                         # Abstract meta-specifications defining core invariants
```

---

## 🚀 Execution & Verification Instructions

Ensure you have the required dependencies installed:
```bash
pip3 install pydantic pytest z3-solver cryptography
```

### 1. Test Suite Verification
To run the full suite of unit and integration tests under Pydantic v2:
```bash
PYTHONPATH=. pytest tests/test_governance.py
```

### 2. Empirical Scenarios Validation
To execute all 53 empirical state transitions, recursion limit checks, and ledger-tampering scenario validations:
```bash
python run_scenarios.py
```

### 3. Infinite-Domain SMT Theorems
To run the automated logical proofs and check that all 8 theorems are successfully proved (or refuted when expected):
```bash
python smt_theorems.py
```

### 4. Release Manifest Freeze & Verification
To freeze and sign the current repository files:
```bash
python freeze_manifest.py
```

To run signature verification, tamper checks, and detect any subsequent code changes on disk:
```bash
python verify_manifest.py
```

---

## 🔮 Next Steps & Upcoming Roadmap

- **K-Induction Support:** Extend the bounded existence checks in SMT proofs to full k-induction over arbitrary path lengths.
- **Hardware Security Modules (HSM):** Introduce integration steps to load manifest signing keys from secure hardware (e.g., YubiKeys or TPMs).
- **Consensus-Backed Ledger Verification:** Transition the single-ledger database into a decentralized, consensus-backed consensus layer.
