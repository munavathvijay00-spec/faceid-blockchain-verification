#!/usr/bin/env python3
"""
Face ID + Blockchain Verification Pipeline
Main CLI Entrypoint
"""

import argparse
from pathlib import Path
import sys
import json
import cv2

from src.config import Config
from src.utils.logger import (
    console,
    print_banner,
    log_step,
    log_info,
    log_success,
    log_warning,
    log_error,
    display_summary_table,
)
from src.utils.image_helpers import load_image, save_image, compute_image_sha256
from src.face_processor import FaceDetector, FaceEncoder
from src.search import ReverseImageSearchEngine
from src.blockchain import AttestationBuilder, EVMBlockchainRecorder

def parse_args():
    parser = argparse.ArgumentParser(
        description="Detect face, find matching social media post via genuine reverse-image search, and anchor to blockchain.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        required=True,
        help="Path to the input image containing a face."
    )
    parser.add_argument(
        "--network",
        "-n",
        type=str,
        default=Config.BLOCKCHAIN_NETWORK,
        choices=["polygon_amoy", "sepolia", "simulator"],
        help="Blockchain network to anchor the match record (default: polygon_amoy)."
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=Config.SEARCH_PROVIDER,
        choices=["serpapi", "serper", "scraper"],
        help="Reverse image search provider (default: scraper/hybrid)."
    )
    parser.add_argument(
        "--hint",
        type=str,
        default=None,
        help="Optional search context hint (e.g., person name) to assist visual entity resolution."
    )
    return parser.parse_args()

def run_pipeline(image_path_str: str, network: str, provider: str, hint: str = None):
    print_banner()
    image_path = Path(image_path_str)

    if not image_path.exists():
        log_error(f"Image file does not exist: {image_path}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # STAGE 1: Image Ingestion & Cryptographic Integrity
    # -------------------------------------------------------------------------
    log_step(1, "Image Ingestion & Integrity Digest", "Hashing original source image")
    log_info(f"Loading input image: [bold cyan]{image_path.name}[/bold cyan] ({image_path.stat().st_size:,} bytes)")
    
    img_bgr = load_image(image_path)
    image_sha256 = compute_image_sha256(image_path)
    log_success(f"Image SHA-256 Digest: [bold yellow]{image_sha256}[/bold yellow]")

    # -------------------------------------------------------------------------
    # STAGE 2: Face Detection & Deep Feature Encoding
    # -------------------------------------------------------------------------
    log_step(2, "Face Detection & Biometric Encoding", "Detecting landmarks and extracting 128-d SFace vector")
    detector = FaceDetector(score_threshold=Config.MIN_FACE_CONFIDENCE)
    detected_faces = detector.detect(img_bgr)

    if not detected_faces:
        log_error("No faces detected in the provided image with confidence above threshold.")
        sys.exit(1)

    primary_face = detected_faces[0]
    log_success(f"Detected {len(detected_faces)} face(s). Primary face confidence: [bold green]{primary_face.confidence*100:.1f}%[/bold green]")
    log_info(f"Face Bounding Box: (x={primary_face.bbox[0]}, y={primary_face.bbox[1]}, w={primary_face.bbox[2]}, h={primary_face.bbox[3]})")

    # Encode face
    encoder = FaceEncoder()
    face_encoding_data = encoder.encode(img_bgr, primary_face)
    log_success(f"Extracted {face_encoding_data['embedding_dim']}-dimensional normalized face embedding")
    log_success(f"Face Biometric Hash: [bold yellow]{face_encoding_data['embedding_hash']}[/bold yellow]")

    # Save output artifacts
    face_crop_path = Config.OUTPUT_DIR / "detected_face.jpg"
    annotated_path = Config.OUTPUT_DIR / "annotated_input.jpg"
    save_image(primary_face.raw_face_crop, face_crop_path)
    annotated_img = detector.draw_detections(img_bgr, [primary_face])
    save_image(annotated_img, annotated_path)
    log_info(f"Saved aligned face crop to: [dim]{face_crop_path}[/dim]")
    log_info(f"Saved annotated image to: [dim]{annotated_path}[/dim]")

    # -------------------------------------------------------------------------
    # STAGE 3: Genuine Reverse-Image Search & Social Match
    # -------------------------------------------------------------------------
    log_step(3, "Genuine Reverse-Image Search", "Executing live visual search for authentic social media posts")
    search_engine = ReverseImageSearchEngine(provider=provider)
    social_matches = search_engine.search(image_path, query_hint=hint)

    if not social_matches:
        log_warning("No matching social media posts found with default query. Retrying with cropped face...")
        social_matches = search_engine.search(face_crop_path, query_hint=hint)

    if not social_matches:
        log_error("Genuine reverse-image search found no matching social media posts. Aborting blockchain upload.")
        sys.exit(1)

    top_match = social_matches[0]
    log_success(f"Found [bold green]{len(social_matches)}[/bold green] verified social media match(es)!")
    log_info(f"Top Matched Platform: [bold magenta]{top_match.platform}[/bold magenta]")
    log_info(f"Verified Post URL:    [bold blue]{top_match.post_url}[/bold blue]")
    log_info(f"Author / Handle:      [bold white]{top_match.author or 'N/A'}[/bold white]")
    log_info(f"Post Title / Snippet: [italic]{top_match.title[:80]}...[/italic]")
    log_info(f"Visual Match Score:   [bold green]{top_match.match_score*100:.1f}%[/bold green]")

    # -------------------------------------------------------------------------
    # STAGE 4: Tamper-Evident Blockchain Anchor
    # -------------------------------------------------------------------------
    log_step(4, "Blockchain Attestation & Ledger Anchor", f"Recording proof to {network.upper()}")
    
    # Construct canonical attestation payload
    attestation_payload = AttestationBuilder.create_payload(
        image_sha256=image_sha256,
        face_encoding_data=face_encoding_data,
        social_match=top_match.to_dict(),
    )
    log_success(f"Constructed Canonical Attestation Hash: [bold yellow]{attestation_payload['attestation_hash']}[/bold yellow]")

    # Submit to blockchain
    recorder = EVMBlockchainRecorder(network=network)
    receipt = recorder.record_match(attestation_payload)

    log_success(f"Anchor Confirmed on [bold cyan]{receipt.network}[/bold cyan]!")
    log_info(f"Transaction Hash: [bold yellow]{receipt.tx_hash}[/bold yellow]")
    log_info(f"Block Number:     {receipt.block_number}")
    log_info(f"Block Explorer:   [underline blue]{receipt.explorer_url}[/underline blue]")

    # Save receipt to output directory
    receipt_path = Config.OUTPUT_DIR / "blockchain_receipt.json"
    receipt_path.write_text(json.dumps(receipt.to_dict(), indent=2))
    log_info(f"Saved complete verifiable receipt to: [dim]{receipt_path}[/dim]")

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    summary = {
        "Input Image": image_path.name,
        "Image SHA-256": f"{image_sha256[:16]}...{image_sha256[-8:]}",
        "Face Confidence": f"{primary_face.confidence*100:.1f}%",
        "Face Hash": f"{face_encoding_data['embedding_hash'][:16]}...",
        "Social Platform": top_match.platform,
        "Verified Post URL": top_match.post_url,
        "Author / Handle": top_match.author or "N/A",
        "Blockchain Network": receipt.network,
        "Block Number": str(receipt.block_number),
        "Transaction Hash": receipt.tx_hash,
        "Block Explorer Link": receipt.explorer_url,
        "Attestation Status": "[bold green]TAMPER-EVIDENT & VERIFIED[/bold green]"
    }
    console.print("")
    display_summary_table(summary)
    console.print(f"\n[bold green]✔ Pipeline successfully completed end-to-end![/bold green]\n")

def main():
    args = parse_args()
    run_pipeline(
        image_path_str=args.image,
        network=args.network,
        provider=args.provider,
        hint=args.hint
    )

if __name__ == "__main__":
    main()
