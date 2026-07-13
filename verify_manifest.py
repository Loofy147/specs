"""
verify_manifest.py
--------------------
The piece that did not exist anywhere in the repo: something that actually
checks a release manifest's signature, and separately re-hashes every listed
artifact from disk to confirm the frozen files still match what was signed.
Two independent failure modes, checked separately, each reported specifically.
"""

import hashlib
import json

import pki
from freeze_manifest_real import canonical_payload, compute_sha256


def verify(manifest_path: str) -> tuple:
    with open(manifest_path) as f:
        manifest = json.load(f)

    reasons = []

    # 1) Signature check
    body = {k: v for k, v in manifest.items() if k not in ("signature", "status")}
    payload = canonical_payload(body)
    signer_pub = pki.pubkey_from_bytes(bytes.fromhex(manifest["signer_public_key"]))
    sig_ok = pki.verify_signature(signer_pub, payload, bytes.fromhex(manifest["signature"]))
    reasons.append(("signature", sig_ok, "Ed25519 signature verifies against embedded signer key" if sig_ok
                     else "signature does NOT verify -- manifest was altered after signing, or wrong key"))

    # 2) Drift check -- do the artifacts on disk still match what was frozen?
    drift = []
    for name, claimed_hash in manifest["artifacts"].items():
        try:
            actual_hash = compute_sha256(name)
        except FileNotFoundError:
            drift.append(f"{name}: file missing from disk")
            continue
        if actual_hash != claimed_hash:
            drift.append(f"{name}: on-disk hash differs from frozen manifest (file changed since freeze)")
    drift_ok = not drift
    reasons.append(("drift", drift_ok, "all artifacts match their frozen hashes" if drift_ok else "; ".join(drift)))

    overall = sig_ok and drift_ok
    return overall, reasons


if __name__ == "__main__":
    import sys
    import dataclasses as dc

    print("=" * 72)
    print("1) Verify the OLD fake manifest (release_manifest.json)")
    print("=" * 72)
    try:
        with open("release_manifest.json") as f:
            old = json.load(f)
        sig_bytes = bytes.fromhex(old["authority_attestation"]["signature"])
        print(f"  claimed signature: {len(sig_bytes)} bytes")
        print(f"  Ed25519 requires:  64 bytes")
        print(f"  no 'signer_public_key' field exists anywhere in this manifest to check it against.")
        print(f"  RESULT: not independently verifiable -- fails before any crypto check is even possible.")
    except Exception as e:
        print(f"  could not even attempt verification: {e}")

    print()
    print("=" * 72)
    print("2) Verify the NEW genuinely-signed manifest (release_manifest_signed.json)")
    print("=" * 72)
    ok, reasons = verify("release_manifest_signed.json")
    for name, r_ok, detail in reasons:
        print(f"  [{'PASS' if r_ok else 'FAIL'}] {name}: {detail}")
    print(f"OVERALL: {'VALID' if ok else 'INVALID'}")
    assert ok, "expected the freshly-signed manifest to verify cleanly"

    print()
    print("=" * 72)
    print("3) Tamper test A: flip one byte of the real signature")
    print("=" * 72)
    with open("release_manifest_signed.json") as f:
        tampered = json.load(f)
    sig = bytearray(bytes.fromhex(tampered["signature"]))
    sig[0] ^= 0xFF
    tampered["signature"] = bytes(sig).hex()
    with open("_tampered_sig.json", "w") as f:
        json.dump(tampered, f)
    ok2, reasons2 = verify("_tampered_sig.json")
    for name, r_ok, detail in reasons2:
        print(f"  [{'PASS' if r_ok else 'FAIL'}] {name}: {detail}")
    print(f"OVERALL: {'VALID' if ok2 else 'INVALID'}  (expected INVALID)")
    assert not ok2

    print()
    print("=" * 72)
    print("4) Tamper test B: edit kernel.py after it was frozen (drift, signature untouched)")
    print("=" * 72)
    with open("kernel.py", "a") as f:
        f.write("\n# innocuous trailing comment added after freeze\n")
    ok3, reasons3 = verify("release_manifest_signed.json")
    for name, r_ok, detail in reasons3:
        print(f"  [{'PASS' if r_ok else 'FAIL'}] {name}: {detail}")
    print(f"OVERALL: {'VALID' if ok3 else 'INVALID'}  (expected INVALID -- drift, even with a valid signature)")
    assert not ok3
    # restore kernel.py exactly
    with open("kernel.py", "r") as f:
        content = f.read()
    with open("kernel.py", "w") as f:
        f.write(content.replace("\n# innocuous trailing comment added after freeze\n", ""))
    print("  (kernel.py restored to its frozen state for repo cleanliness)")
