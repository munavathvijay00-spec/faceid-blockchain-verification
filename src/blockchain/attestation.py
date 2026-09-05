"""Tamper-evident attestation payload generator and cryptographic proof utilities."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Dict, Any

class AttestationBuilder:
    """Constructs canonical tamper-evident payloads for blockchain recording."""

    SCHEMA_VERSION = "1.0.0"

    @classmethod
    def create_payload(
        cls,
        image_sha256: str,
        face_encoding_data: Dict[str, Any],
        social_match: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Builds a structured, deterministic attestation dictionary.
        """
        payload = {
            "schema_version": cls.SCHEMA_VERSION,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "image_integrity": {
                "sha256": image_sha256,
            },
            "face_biometric_proof": {
                "confidence": face_encoding_data.get("confidence"),
                "bbox": face_encoding_data.get("bbox"),
                "embedding_dim": face_encoding_data.get("embedding_dim"),
                "embedding_hash": face_encoding_data.get("embedding_hash"),
            },
            "verified_social_match": {
                "platform": social_match.get("platform"),
                "post_url": social_match.get("post_url"),
                "author": social_match.get("author"),
                "title": social_match.get("title"),
                "match_score": social_match.get("match_score"),
            },
        }

        # Calculate canonical SHA-256 hash of the entire attestation
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        attestation_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        payload["attestation_hash"] = f"0x{attestation_hash}"
        return payload

    @classmethod
    def serialize_for_chain(cls, payload: Dict[str, Any]) -> str:
        """Serializes payload into canonical JSON string."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def verify_integrity(cls, payload: Dict[str, Any]) -> bool:
        """Verifies that the attestation_hash matches the canonical payload."""
        if "attestation_hash" not in payload:
            return False

        recorded_hash = payload["attestation_hash"]
        clone = dict(payload)
        del clone["attestation_hash"]

        canonical_json = json.dumps(clone, sort_keys=True, separators=(",", ":"))
        computed_hash = f"0x{hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()}"

        return recorded_hash.lower() == computed_hash.lower()
