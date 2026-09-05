"""Face feature encoding using OpenCV SFace deep neural network."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import hashlib
import json
import cv2
import numpy as np

from .detector import DetectedFace

class FaceEncoder:
    """Generates 128-dimensional facial embedding vectors using SFace."""

    def __init__(self, model_path: Optional[Path] = None):
        if model_path is None:
            model_path = Path(__file__).resolve().parent.parent.parent / "models" / "face_recognition_sface_2021dec.onnx"
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"SFace model not found at {self.model_path}")

        self.recognizer = cv2.FaceRecognizerSF.create(str(self.model_path), "")

    def encode(self, original_image: np.ndarray, detected_face: DetectedFace) -> Dict:
        """
        Extracts aligned face crop, computes normalized 128-d feature vector,
        and generates cryptographic hash of the embedding.
        """
        # If we have YuNet detection array, use SFace's built-in alignCrop
        if detected_face.raw_detection_array is not None:
            aligned_face = self.recognizer.alignCrop(original_image, detected_face.raw_detection_array)
            feature = self.recognizer.feature(aligned_face)
        else:
            # Resize crop to 112x112 standard input for SFace
            aligned_face = cv2.resize(detected_face.raw_face_crop, (112, 112))
            feature = self.recognizer.feature(aligned_face)

        # Normalize feature vector (L2 norm)
        embedding_raw = feature.flatten()
        norm = np.linalg.norm(embedding_raw)
        if norm > 0:
            embedding = embedding_raw / norm
        else:
            embedding = embedding_raw

        embedding_list = [round(float(v), 6) for v in embedding]

        # Compute deterministic SHA-256 hash of the embedding vector
        serialized = json.dumps(embedding_list, sort_keys=True)
        embedding_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return {
            "embedding": embedding_list,
            "embedding_dim": len(embedding_list),
            "embedding_hash": f"0x{embedding_hash}",
            "aligned_face": aligned_face,
            "bbox": list(detected_face.bbox),
            "confidence": round(detected_face.confidence, 4),
        }

    @staticmethod
    def cosine_similarity(feat1: Union[np.ndarray, List[float]], feat2: Union[np.ndarray, List[float]]) -> float:
        """Computes cosine similarity between two face feature vectors."""
        v1 = np.array(feat1, dtype=np.float32)
        v2 = np.array(feat2, dtype=np.float32)
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (n1 * n2))
