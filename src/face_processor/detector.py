"""Face detection using OpenCV YuNet with Haar Cascade fallback."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.utils.logger import log_info, log_warning
from src.utils.image_helpers import crop_bounding_box, load_image

@dataclass
class DetectedFace:
    """Represents a detected face in an image."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float
    landmarks: Optional[List[Tuple[float, float]]]  # 5 landmarks: right_eye, left_eye, nose, right_mouth, left_mouth
    raw_face_crop: np.ndarray
    raw_detection_array: Optional[np.ndarray] = None  # Full 15-element array from YuNet for SFace alignment

class FaceDetector:
    """Detects faces in images using YuNet with Haar Cascade fallback."""

    def __init__(self, model_dir: Optional[Path] = None, score_threshold: float = 0.6):
        self.score_threshold = score_threshold
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        self.model_dir = Path(model_dir)

        self.yunet_model_path = self.model_dir / "face_detection_yunet_2023mar.onnx"
        self.haar_model_path = self.model_dir / "haarcascade_frontalface_default.xml"

        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """Initializes primary YuNet detector or falls back to Haar cascade."""
        if self.yunet_model_path.exists():
            try:
                # Initialize YuNet with a dummy size (will be updated per image)
                self.detector = cv2.FaceDetectorYN.create(
                    str(self.yunet_model_path),
                    "",
                    (320, 320),
                    score_threshold=self.score_threshold,
                    nms_threshold=0.3,
                    top_k=5000
                )
                self.backend = "yunet"
                return
            except Exception as e:
                log_warning(f"Failed to initialize YuNet: {e}. Falling back to Haar cascade.")

        # Fallback to Haar Cascade
        if self.haar_model_path.exists():
            self.detector = cv2.CascadeClassifier(str(self.haar_model_path))
            self.backend = "haar"
        else:
            raise FileNotFoundError("No valid face detection model found in models/ directory.")

    def detect(self, image_source: np.ndarray) -> List[DetectedFace]:
        """
        Detects faces in an input image.
        Returns a list of DetectedFace objects ordered by confidence/size.
        """
        img = image_source.copy()
        h, w = img.shape[:2]
        detected_faces = []

        if self.backend == "yunet":
            # Set input size to image dimensions
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img)

            if faces is not None and len(faces) > 0:
                for face in faces:
                    # YuNet output: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rc, y_rc, x_lc, y_lc, score]
                    bx, by, bw, bh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    score = float(face[-1])

                    # Extract 5 landmarks
                    landmarks = [
                        (float(face[4]), float(face[5])),   # right eye
                        (float(face[6]), float(face[7])),   # left eye
                        (float(face[8]), float(face[9])),   # nose tip
                        (float(face[10]), float(face[11])), # right mouth corner
                        (float(face[12]), float(face[13]))  # left mouth corner
                    ]

                    crop = crop_bounding_box(img, (bx, by, bw, bh), margin=0.15)
                    detected_faces.append(
                        DetectedFace(
                            bbox=(bx, by, bw, bh),
                            confidence=score,
                            landmarks=landmarks,
                            raw_face_crop=crop,
                            raw_detection_array=face
                        )
                    )
        else:
            # Haar cascade fallback
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            for (bx, by, bw, bh) in faces:
                crop = crop_bounding_box(img, (bx, by, bw, bh), margin=0.15)
                detected_faces.append(
                    DetectedFace(
                        bbox=(int(bx), int(by), int(bw), int(bh)),
                        confidence=0.85,
                        landmarks=None,
                        raw_face_crop=crop,
                        raw_detection_array=None
                    )
                )

        # Sort by confidence descending
        detected_faces.sort(key=lambda f: f.confidence, reverse=True)
        return detected_faces

    def draw_detections(self, image: np.ndarray, faces: List[DetectedFace]) -> np.ndarray:
        """Draws bounding boxes and landmarks on the image."""
        annotated = image.copy()
        for idx, face in enumerate(faces):
            x, y, w, h = face.bbox
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"Face #{idx+1}: {face.confidence*100:.1f}%"
            cv2.putText(
                annotated,
                label,
                (x, max(15, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2
            )

            # Draw landmarks if present
            if face.landmarks:
                colors = [(255, 0, 0), (0, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255)]
                for pt, col in zip(face.landmarks, colors):
                    cv2.circle(annotated, (int(pt[0]), int(pt[1])), 3, col, -1)

        return annotated
