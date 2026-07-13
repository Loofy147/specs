"""
freeze_manifest_real.py
-------------------------
Replaces freeze_manifest.py's "authority_attestation" -- which is a hardcoded,
37-byte, non-Ed25519, non-recomputed string that never changes no matter what
the artifacts contain (see AUDIT_NOTE.md) -- with a genuine Ed25519 signature
over the actual manifest content, using the SAME pki.py already in this repo.

This is meant to be paired with verify_manifest.py, which is the piece that
was entirely missing: nothing anywhere in the repo checked the old signature
against anything. A signature nobody verifies is not an attestation.
"""

import hashlib
import json
import datetime

import pki

FILES_TO_FREEZE = {
    "governance_math.tex": "governance_math.tex",
    "kernel.py": "kernel.py",
    "atomic_engines.py": "atomic_engines.py",
    "smt_theorems.py": "smt_theorems.py",
    "pki.py": "pki.py",
}


def compute_sha256(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def canonical_payload(manifest_body: dict) -> bytes:
    """Deterministic byte encoding of exactly what gets signed."""
    return json.dumps(manifest_body, sort_keys=True).encode()


def build_and_sign(root: pki.KeyPair) -> dict:
    artifacts = {}
    for key, path in FILES_TO_FREEZE.items():
        try:
            artifacts[key] = compute_sha256(path)
        except FileNotFoundError:
            print(f"Warning: {path} not found, skipping.")

    body = {
        "version": "2.0.0-canonical-signed",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "artifacts": artifacts,
        "signer_public_key": root.public_bytes().hex(),
        "signer_fingerprint": root.fingerprint(),
    }
    payload = canonical_payload(body)
    signature = root.sign(payload)

    manifest = dict(body)
    manifest["signature"] = signature.hex()
    manifest["status"] = "FROZEN_AND_LOCKED"
    return manifest


if __name__ == "__main__":
    # In production this key is generated once, kept offline, and its public
    # half is the thing that gets distributed/pinned -- generating fresh here
    # is only for this demonstration.
    root = pki.generate_keypair()
    manifest = build_and_sign(root)

    with open("release_manifest_signed.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("MANIFEST CREATED AND GENUINELY SIGNED")
    print(f"  signer fingerprint: {manifest['signer_fingerprint']}")
    print(f"  signature length:   {len(bytes.fromhex(manifest['signature']))} bytes (Ed25519 = 64)")
