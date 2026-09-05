#!/usr/bin/env bash
# ==============================================================================
# Face ID + Blockchain Verification Pipeline - End-to-End Demo Script
# ==============================================================================
# This script executes the complete pipeline end-to-end for screen recording:
# 1. Runs face detection and feature encoding on an input image
# 2. Performs live genuine reverse-image search for matching social media post
# 3. Anchors the tamper-evident attestation onto the blockchain
# 4. Runs independent cryptographic verification
# ==============================================================================

set -e

# Detect python executable
if [ -d ".venv" ]; then
    PYTHON="./.venv/bin/python"
else
    PYTHON="python3"
fi

echo "======================================================================"
echo " Starting Full End-to-End Pipeline Demo..."
echo "======================================================================"

# Run main pipeline
$PYTHON main.py --image samples/elon_musk.jpg

# Extract transaction hash from generated receipt
TX_HASH=$($PYTHON -c "import json; data=json.load(open('output/blockchain_receipt.json')); print(data['tx_hash'])")

echo ""
echo "======================================================================"
echo " Running Independent On-Chain Cryptographic Verification..."
echo " Target TX: $TX_HASH"
echo "======================================================================"

# Verify matching image
$PYTHON verify_record.py --tx "$TX_HASH" --image samples/elon_musk.jpg

echo ""
echo "======================================================================"
echo " Testing Tamper Detection with Unmatched Image..."
echo "======================================================================"

# Verify tamper detection on different candidate image
$PYTHON verify_record.py --tx "$TX_HASH" --image samples/sample_face1.jpg || true

echo ""
echo "======================================================================"
echo " Demo Completed Successfully!"
echo " Review generated outputs in: ./output/"
echo "======================================================================"
