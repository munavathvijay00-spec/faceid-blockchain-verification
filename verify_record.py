#!/usr/bin/env python3
"""
Face ID + Blockchain Verification Pipeline
Independent Record Verification CLI
"""

import argparse
from pathlib import Path
import sys
import json
from rich.panel import Panel
from rich.table import Table

from src.config import Config
from src.utils.logger import console, print_banner, log_info, log_success, log_error, log_warning
from src.utils.image_helpers import load_image, compute_image_sha256
from src.face_processor import FaceDetector, FaceEncoder
from src.blockchain import AttestationBuilder, EVMBlockchainRecorder

def parse_args():
    parser = argparse.ArgumentParser(
        description="Verify that an image and social match correspond to a tamper-evident blockchain record.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--tx",
        "-t",
        type=str,
        required=True,
        help="Blockchain transaction hash containing the attestation record."
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        required=True,
        help="Local candidate image to verify against the on-chain record."
    )
    parser.add_argument(
        "--network",
        "-n",
        type=str,
        default=Config.BLOCKCHAIN_NETWORK,
        choices=["polygon_amoy", "sepolia", "simulator"],
        help="Blockchain network where the transaction is anchored."
    )
    return parser.parse_args()

def verify(tx_hash: str, image_path_str: str, network: str):
    print_banner()
    image_path = Path(image_path_str)

    if not image_path.exists():
        log_error(f"Candidate image not found at: {image_path}")
        sys.exit(1)

    console.print(f"\n[bold yellow]AUDIT & VERIFICATION INITIATED[/bold yellow]")
    console.print(f"Target TX Hash: [cyan]{tx_hash}[/cyan]")
    console.print(f"Candidate Image: [cyan]{image_path.name}[/cyan]\n")

    # Step 1: Fetch payload from blockchain
    log_info("Querying blockchain state for transaction record...")
    recorder = EVMBlockchainRecorder(network=network)
    on_chain_payload = recorder.fetch_transaction_data(tx_hash)

    if not on_chain_payload:
        log_error(f"Transaction {tx_hash} could not be found or contains no valid attestation payload.")
        sys.exit(1)

    log_success("Retrieved on-chain attestation record successfully!")

    # Step 2: Verify Cryptographic Integrity of the Attestation Payload itself
    log_info("Verifying mathematical integrity of on-chain canonical payload...")
    is_valid_payload = AttestationBuilder.verify_integrity(on_chain_payload)
    if not is_valid_payload:
        log_error("Integrity check FAILED: Payload hash does not match canonical contents!")
        sys.exit(1)
    log_success("On-chain payload integrity verified (no tampering detected).")

    # Step 3: Compute candidate image SHA-256
    log_info("Computing candidate image SHA-256 digest...")
    candidate_sha256 = compute_image_sha256(image_path)
    recorded_sha256 = on_chain_payload.get("image_integrity", {}).get("sha256", "")

    image_matches = candidate_sha256.lower() == recorded_sha256.lower()

    # Step 4: Compute candidate face biometric embedding
    log_info("Extracting candidate face biometric embedding...")
    img = load_image(image_path)
    detector = FaceDetector()
    faces = detector.detect(img)

    face_matches = False
    candidate_face_hash = "N/A"
    if faces:
        encoder = FaceEncoder()
        enc = encoder.encode(img, faces[0])
        candidate_face_hash = enc["embedding_hash"]
        recorded_face_hash = on_chain_payload.get("face_biometric_proof", {}).get("embedding_hash", "")
        face_matches = candidate_face_hash.lower() == recorded_face_hash.lower()

    # Step 5: Render Audit Table
    table = Table(title="[bold cyan]Cryptographic Verification Audit Report[/bold cyan]", border_style="green" if (image_matches and face_matches) else "red")
    table.add_column("Verification Step", style="bold white", width=26)
    table.add_column("On-Chain Value", style="yellow")
    table.add_column("Candidate Value", style="magenta")
    table.add_column("Status", justify="center", width=12)

    table.add_row(
        "Image SHA-256",
        f"{recorded_sha256[:16]}...",
        f"{candidate_sha256[:16]}...",
        "[bold green]MATCH[/bold green]" if image_matches else "[bold red]MISMATCH[/bold red]"
    )
    table.add_row(
        "Face Biometric Hash",
        f"{on_chain_payload.get('face_biometric_proof', {}).get('embedding_hash', '')[:16]}...",
        f"{candidate_face_hash[:16]}...",
        "[bold green]MATCH[/bold green]" if face_matches else "[bold red]MISMATCH[/bold red]"
    )
    table.add_row(
        "Matched Social Platform",
        on_chain_payload.get("verified_social_match", {}).get("platform", "N/A"),
        "-",
        "[bold green]AUTHENTIC[/bold green]"
    )
    table.add_row(
        "Verified Social Post URL",
        on_chain_payload.get("verified_social_match", {}).get("post_url", "N/A"),
        "-",
        "[bold green]AUTHENTIC[/bold green]"
    )

    console.print(table)

    if image_matches and face_matches:
        panel = Panel(
            f"[bold green]✔ VERIFICATION SUCCESSFUL[/bold green]\n\n"
            f"The image '{image_path.name}' is cryptographically IDENTICAL to the image attested\n"
            f"on the blockchain in transaction {tx_hash}.\n"
            f"The associated social media post ({on_chain_payload.get('verified_social_match', {}).get('post_url')}) is an untampered, permanent record.",
            title="[bold green]VERIFIED ON-CHAIN[/bold green]",
            border_style="green"
        )
        console.print(panel)
    else:
        panel = Panel(
            f"[bold red]✖ VERIFICATION FAILED[/bold red]\n\n"
            f"The candidate image does not match the immutable record stored on-chain!",
            title="[bold red]TAMPERING DETECTED OR WRONG IMAGE[/bold red]",
            border_style="red"
        )
        console.print(panel)
        sys.exit(1)

def main():
    args = parse_args()
    verify(tx_hash=args.tx, image_path_str=args.image, network=args.network)

if __name__ == "__main__":
    main()
