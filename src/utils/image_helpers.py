"""Image processing helpers, hashing, and formatting."""

import hashlib
import base64
from pathlib import Path
from typing import Union, Tuple
import cv2
import numpy as np
from PIL import Image

def compute_image_sha256(source: Union[str, Path, bytes, np.ndarray]) -> str:
    """
    Computes a cryptographic SHA-256 digest of image bytes or numpy array.
    """
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()
    elif isinstance(source, bytes):
        return hashlib.sha256(source).hexdigest()
    elif isinstance(source, np.ndarray):
        success, encoded = cv2.imencode(".jpg", source)
        if success:
            return hashlib.sha256(encoded.tobytes()).hexdigest()
        return hashlib.sha256(source.tobytes()).hexdigest()
    else:
        raise ValueError(f"Unsupported image source type: {type(source)}")

def load_image(image_path: Union[str, Path]) -> np.ndarray:
    """
    Loads an image from file path using OpenCV.
    """
    path_str = str(image_path)
    if not Path(path_str).exists():
        raise FileNotFoundError(f"Image not found at {path_str}")
    img = cv2.imread(path_str)
    if img is None:
        raise ValueError(f"Failed to decode image from {path_str}")
    return img

def save_image(img: np.ndarray, output_path: Union[str, Path]) -> str:
    """
    Saves an image to disk.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)
    return str(output_path)

def crop_bounding_box(img: np.ndarray, bbox: Tuple[int, int, int, int], margin: float = 0.1) -> np.ndarray:
    """
    Crops region from image with an optional fractional margin.
    bbox format: (x, y, width, height)
    """
    h, w = img.shape[:2]
    x, y, bw, bh = bbox

    # Expand margin
    mx = int(bw * margin)
    my = int(bh * margin)

    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(w, x + bw + mx)
    y2 = min(h, y + bh + my)

    return img[y1:y2, x1:x2]

def encode_image_base64(image_path: Union[str, Path]) -> str:
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
