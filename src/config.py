"""Configuration module for Face ID + Blockchain Verification Pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    """Application configuration."""

    # Search Provider settings
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "scraper").lower()
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()

    # Blockchain settings
    BLOCKCHAIN_NETWORK = os.getenv("BLOCKCHAIN_NETWORK", "polygon_amoy").lower()
    POLYGON_AMOY_RPC = os.getenv("POLYGON_AMOY_RPC", "https://rpc-amoy.polygon.technology")
    SEPOLIA_RPC = os.getenv("SEPOLIA_RPC", "https://ethereum-sepolia-rpc.publicnode.com")
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "").strip()
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "").strip()

    # Chain IDs and Explorer URLs
    NETWORKS = {
        "polygon_amoy": {
            "name": "Polygon Amoy Testnet",
            "chain_id": 80002,
            "rpc_url": POLYGON_AMOY_RPC,
            "explorer_tx_url": "https://amoy.polygonscan.com/tx/",
            "currency_symbol": "POL",
        },
        "sepolia": {
            "name": "Ethereum Sepolia Testnet",
            "chain_id": 11155111,
            "rpc_url": SEPOLIA_RPC,
            "explorer_tx_url": "https://sepolia.etherscan.io/tx/",
            "currency_symbol": "ETH",
        },
        "simulator": {
            "name": "Local Tamper-Evident Ledger (Simulator)",
            "chain_id": 1337,
            "rpc_url": "http://127.0.0.1:8545",
            "explorer_tx_url": "https://amoy.polygonscan.com/tx/",
            "currency_symbol": "TEST",
        }
    }

    # Pipeline parameters
    MIN_FACE_CONFIDENCE = float(os.getenv("MIN_FACE_CONFIDENCE", "0.60"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))

    # Recognized social media domains
    SOCIAL_MEDIA_DOMAINS = [
        "twitter.com",
        "x.com",
        "linkedin.com",
        "instagram.com",
        "reddit.com",
        "facebook.com",
        "threads.net",
        "youtube.com",
        "tiktok.com",
        "medium.com",
        "github.com",
        "pinterest.com",
    ]

# Ensure output directory exists
Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
