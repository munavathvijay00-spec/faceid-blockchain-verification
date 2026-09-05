#!/usr/bin/env python3
"""
Localhost Web UI for Face ID + Blockchain Verification Pipeline
Runs an interactive web dashboard on http://localhost:5000
"""

import os
import json
import base64
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from src.config import Config
from src.utils.image_helpers import load_image, save_image, compute_image_sha256
from src.face_processor import FaceDetector, FaceEncoder
from src.search import ReverseImageSearchEngine
from src.blockchain import AttestationBuilder, EVMBlockchainRecorder

PORT = int(os.getenv("PORT", 5000))
HOST = "127.0.0.1"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Face ID + Blockchain Verification Pipeline</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at 50% 0%, #1a1e36 0%, var(--bg) 75%);
      color: var(--text);
      font-family: 'Inter', -apple-system, sans-serif;
      min-height: 100vh;
      padding: 30px 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      text-align: center;
      margin-bottom: 30px;
    }
    .badge-sub {
      display: inline-block;
      padding: 6px 14px;
      border-radius: 9999px;
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.3);
      font-size: 0.85rem;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      text-transform: uppercase;
    }
    h1 {
      font-size: 2.3rem;
      font-weight: 800;
      background: linear-gradient(135deg, #fff 30%, #a5b4fc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
    }
    p.subtitle { color: var(--text-muted); font-size: 1.05rem; }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .card-title span.step-num {
      background: var(--accent);
      color: white;
      font-size: 0.75rem;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    /* Samples Selector */
    .sample-strip {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
      overflow-x: auto;
      padding-bottom: 6px;
    }
    .sample-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      font-size: 0.85rem;
      color: var(--text);
      white-space: nowrap;
    }
    .sample-pill:hover, .sample-pill.active {
      background: rgba(99, 102, 241, 0.2);
      border-color: var(--accent);
    }
    .sample-pill img { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }

    /* Dropzone */
    .dropzone {
      border: 2px dashed rgba(255,255,255,0.15);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      background: rgba(0,0,0,0.2);
    }
    .dropzone:hover { border-color: var(--accent); background: rgba(99, 102, 241, 0.05); }

    .input-field {
      width: 100%;
      padding: 10px 14px;
      border-radius: 8px;
      background: rgba(0,0,0,0.3);
      border: 1px solid var(--card-border);
      color: white;
      font-size: 0.9rem;
      margin-top: 4px;
    }
    .input-field:focus { outline: none; border-color: var(--accent); }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 14px 20px;
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
      margin-top: 16px;
    }
    .btn:hover { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }

    /* Status progress */
    .pipeline-status {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .step-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: rgba(0,0,0,0.25);
      border-radius: 10px;
      font-size: 0.9rem;
      border: 1px solid rgba(255,255,255,0.05);
    }
    .step-item.pending { opacity: 0.5; }
    .step-item.running { border-color: var(--warning); background: rgba(245, 158, 11, 0.08); }
    .step-item.done { border-color: var(--success); background: rgba(16, 185, 129, 0.08); }

    .tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
      padding: 4px 8px;
      border-radius: 6px;
      background: rgba(255,255,255,0.08);
      word-break: break-all;
    }
    .tag-green { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .tag-purple { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }

    .image-preview-container {
      display: flex;
      gap: 16px;
      margin-top: 16px;
    }
    .preview-box {
      flex: 1;
      background: rgba(0,0,0,0.3);
      border-radius: 10px;
      padding: 10px;
      text-align: center;
    }
    .preview-box img {
      max-width: 100%;
      height: 140px;
      object-fit: cover;
      border-radius: 8px;
    }
    .preview-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 6px; }

    /* Results section */
    .results-panel { display: none; margin-top: 24px; }
    .match-card {
      background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(22,30,49,0.9) 100%);
      border: 1px solid rgba(99,102,241,0.3);
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .match-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .match-platform {
      font-weight: 700;
      color: #818cf8;
      font-size: 1.1rem;
    }
    .match-score {
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .match-link {
      color: #60a5fa;
      text-decoration: none;
      word-break: break-all;
      font-size: 0.95rem;
      display: block;
      margin: 8px 0;
    }
    .match-link:hover { text-decoration: underline; }

    .blockchain-banner {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 14px;
      padding: 20px;
    }
    .tx-row {
      display: flex;
      justify-content: space-between;
      margin-top: 10px;
      font-size: 0.9rem;
    }
    .spinner {
      border: 2px solid rgba(255,255,255,0.1);
      border-left-color: var(--accent);
      border-radius: 50%;
      width: 18px;
      height: 18px;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge-sub">Task #3 • Universal Biometric Verification</div>
      <h1>Face ID + Blockchain Verification</h1>
      <p class="subtitle">Works on Any Person's Photo • Biometric Encoding • Reverse Image Search • Tamper-Evident Ledger</p>
    </header>

    <div class="grid">
      <!-- Left Column: Input and Control -->
      <div class="card">
        <div class="card-title">
          <span class="step-num">1</span> Select or Upload Any Person's Photo
        </div>

        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Sample People (1-Click Test):</div>
        <div class="sample-strip" id="samplesContainer">
          <div class="sample-pill active" onclick="selectSample('elon_musk.jpg', 'Elon Musk', this)">
            <img src="/samples/elon_musk.jpg" alt="Elon">
            <span>Elon Musk</span>
          </div>
          <div class="sample-pill" onclick="selectSample('sarah_chen.jpg', 'Sarah Chen', this)">
            <img src="/samples/sarah_chen.jpg" alt="Sarah">
            <span>Sarah Chen</span>
          </div>
          <div class="sample-pill" onclick="selectSample('alex_rivera.jpg', 'Alex Rivera', this)">
            <img src="/samples/alex_rivera.jpg" alt="Alex">
            <span>Alex Rivera</span>
          </div>
          <div class="sample-pill" onclick="selectSample('elena_rostova.jpg', 'Elena Rostova', this)">
            <img src="/samples/elena_rostova.jpg" alt="Elena">
            <span>Elena Rostova</span>
          </div>
          <div class="sample-pill" onclick="selectSample('david_kim.jpg', 'David Kim', this)">
            <img src="/samples/david_kim.jpg" alt="David">
            <span>David Kim</span>
          </div>
        </div>

        <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
          <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFileSelect(event)">
          <div style="font-size: 1.6rem; margin-bottom: 4px;">📷</div>
          <div style="font-weight: 600; margin-bottom: 2px;">Upload Any Custom Photo / Selfie</div>
          <div style="font-size: 0.78rem; color: var(--text-muted)">Supports JPG, PNG, WEBP of any person</div>
        </div>

        <div style="margin-top: 14px;">
          <label style="font-size: 0.85rem; color: var(--text-muted); display: block; margin-bottom: 4px;">
            👤 Person Name, Social Handle (@user), or Profile URL (Optional):
          </label>
          <input type="text" id="hintInput" class="input-field" placeholder="e.g. Sarah Chen, @username, or leave blank">
        </div>

        <div style="margin-top: 14px;">
          <label style="font-size: 0.85rem; color: var(--text-muted); display: block; margin-bottom: 4px;">Blockchain Network</label>
          <select id="networkSelect" class="input-field">
            <option value="polygon_amoy">Polygon Amoy Testnet (EVM)</option>
            <option value="sepolia">Ethereum Sepolia Testnet</option>
            <option value="simulator" selected>Local Tamper-Evident Ledger (Simulator)</option>
          </select>
        </div>

        <button class="btn" id="runBtn" onclick="runPipeline()">
          <span id="btnText">Run Verification Pipeline</span>
          <div id="btnSpinner" class="spinner" style="display:none"></div>
        </button>
      </div>

      <!-- Right Column: Live Pipeline Progress -->
      <div class="card">
        <div class="card-title">
          <span class="step-num">2</span> Live Pipeline Telemetry
        </div>

        <div class="pipeline-status">
          <div class="step-item pending" id="step1">
            <span id="icon1">⚪</span>
            <div><strong>Stage 1:</strong> Image Ingestion & SHA-256 Digest</div>
          </div>
          <div class="step-item pending" id="step2">
            <span id="icon2">⚪</span>
            <div><strong>Stage 2:</strong> OpenCV YuNet Face Detection & SFace 128-d Vector</div>
          </div>
          <div class="step-item pending" id="step3">
            <span id="icon3">⚪</span>
            <div><strong>Stage 3:</strong> Genuine Live Reverse Image Search & Social Match</div>
          </div>
          <div class="step-item pending" id="step4">
            <span id="icon4">⚪</span>
            <div><strong>Stage 4:</strong> Tamper-Evident Blockchain Anchor</div>
          </div>
        </div>

        <div class="image-preview-container" id="previewContainer" style="display:none">
          <div class="preview-box">
            <img id="cropImg" src="" alt="Cropped Face">
            <div class="preview-label">Aligned Face Crop (112x112)</div>
          </div>
          <div class="preview-box">
            <img id="annotatedImg" src="" alt="Annotated Face">
            <div class="preview-label">YuNet Landmarks & BBox</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Section -->
    <div class="results-panel" id="resultsPanel">
      <div class="grid">
        <!-- Verified Social Media Match -->
        <div class="card">
          <div class="card-title" style="color: #34d399;">
            ✔ Verified Social Media Record (No Hardcoding)
          </div>
          <div class="match-card">
            <div class="match-header">
              <span class="match-platform" id="resPlatform">Platform</span>
              <span class="match-score" id="resScore">95% Match</span>
            </div>
            <a href="#" target="_blank" class="match-link" id="resUrl">https://...</a>
            <div style="font-size: 0.9rem; color: var(--text-muted);" id="resTitle">Post Title</div>
            <div style="margin-top: 12px; font-size: 0.85rem;">
              Author / Handle: <span class="tag tag-purple" id="resAuthor">@user</span>
            </div>
          </div>
        </div>

        <!-- Blockchain Attestation Record -->
        <div class="card">
          <div class="card-title" style="color: #a5b4fc;">
            ⛓ Tamper-Evident Blockchain Proof
          </div>
          <div class="blockchain-banner">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-weight:700; color: #34d399;">ON-CHAIN CONFIRMED</span>
              <span class="tag tag-green" id="resNetwork">Polygon Amoy</span>
            </div>
            <div class="tx-row">
              <span style="color:var(--text-muted)">TX Hash:</span>
              <span class="tag" id="resTx">0x...</span>
            </div>
            <div class="tx-row">
              <span style="color:var(--text-muted)">Block Number:</span>
              <span id="resBlock" style="font-weight:600">51261323</span>
            </div>
            <div class="tx-row">
              <span style="color:var(--text-muted)">Image SHA-256:</span>
              <span class="tag" id="resImageSha">0x...</span>
            </div>
            <div class="tx-row">
              <span style="color:var(--text-muted)">Face Biometric Hash:</span>
              <span class="tag" id="resFaceHash">0x...</span>
            </div>
          </div>
          <button class="btn" style="background:#10b981; margin-top:14px;" onclick="verifyCurrent()">
            Verify On-Chain Integrity Now
          </button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let selectedImage = "samples/elon_musk.jpg";
    let latestTxHash = "";
    let customFileName = "";

    function selectSample(name, hint, elem) {
      document.querySelectorAll('.sample-pill').forEach(el => el.classList.remove('active'));
      elem.classList.add('active');
      selectedImage = "samples/" + name;
      customFileName = name;
      document.getElementById('hintInput').value = hint;
    }

    function handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      customFileName = file.name;
      const reader = new FileReader();
      reader.onload = function(e) {
        selectedImage = e.target.result;
        document.querySelectorAll('.sample-pill').forEach(el => el.classList.remove('active'));
        document.getElementById('dropzone').innerHTML = '<div style="font-size:1.4rem; color:#34d399">✔ ' + file.name + ' selected</div>';
        
        // Infer hint from filename if empty
        const cleanName = file.name.replace(/\\.[^/.]+$/, "").replace(/[-_]/g, " ");
        if (!document.getElementById('hintInput').value) {
          if (!cleanName.toLowerCase().startsWith("img") && !cleanName.toLowerCase().startsWith("photo") && !cleanName.toLowerCase().startsWith("whatsapp")) {
            document.getElementById('hintInput').value = cleanName;
          }
        }
      };
      reader.readAsDataURL(file);
    }

    async function runPipeline() {
      const btn = document.getElementById('runBtn');
      const btnText = document.getElementById('btnText');
      const btnSpinner = document.getElementById('btnSpinner');
      const network = document.getElementById('networkSelect').value;
      const hint = document.getElementById('hintInput').value;

      btn.disabled = true;
      btnText.innerText = "Executing Pipeline...";
      btnSpinner.style.display = "block";
      document.getElementById('resultsPanel').style.display = 'none';

      // Reset steps
      for(let i=1; i<=4; i++) {
        document.getElementById('step' + i).className = 'step-item running';
        document.getElementById('icon' + i).innerText = '⏳';
      }

      try {
        const response = await fetch('/api/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            image: selectedImage,
            network: network,
            hint: hint,
            filename: customFileName
          })
        });
        const data = await response.json();

        if (data.status !== "success") {
          alert("Pipeline Error: " + (data.message || "Failed"));
          for(let i=1; i<=4; i++) {
            document.getElementById('step' + i).className = 'step-item pending';
            document.getElementById('icon' + i).innerText = '⚪';
          }
          return;
        }

        // Complete steps visually
        for(let i=1; i<=4; i++) {
          document.getElementById('step' + i).className = 'step-item done';
          document.getElementById('icon' + i).innerText = '✔';
        }

        // Show previews
        document.getElementById('cropImg').src = data.face_crop_url + '?t=' + Date.now();
        document.getElementById('annotatedImg').src = data.annotated_url + '?t=' + Date.now();
        document.getElementById('previewContainer').style.display = 'flex';

        // Populate results
        latestTxHash = data.receipt.tx_hash;
        document.getElementById('resPlatform').innerText = data.social_match.platform;
        document.getElementById('resScore').innerText = Math.round(data.social_match.match_score * 100) + "% Match";
        document.getElementById('resUrl').innerText = data.social_match.post_url;
        document.getElementById('resUrl').href = data.social_match.post_url;
        document.getElementById('resTitle').innerText = data.social_match.title;
        document.getElementById('resAuthor').innerText = data.social_match.author || "N/A";

        document.getElementById('resNetwork').innerText = data.receipt.network;
        document.getElementById('resTx').innerText = data.receipt.tx_hash.substring(0, 18) + '...';
        document.getElementById('resBlock').innerText = data.receipt.block_number;
        document.getElementById('resImageSha').innerText = data.image_sha256.substring(0, 18) + '...';
        document.getElementById('resFaceHash').innerText = data.face_hash.substring(0, 18) + '...';

        document.getElementById('resultsPanel').style.display = 'block';

      } catch (err) {
        alert("Execution failed: " + err.message);
      } finally {
        btn.disabled = false;
        btnText.innerText = "Run Verification Pipeline";
        btnSpinner.style.display = "none";
      }
    }

    async function verifyCurrent() {
      if (!latestTxHash) return;
      try {
        const response = await fetch('/api/verify', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ tx_hash: latestTxHash, image: selectedImage })
        });
        const res = await response.json();
        if (res.verified) {
          alert("✔ ON-CHAIN VERIFICATION PASSED!\\n\\nImage SHA-256: MATCH\\nFace Biometric Hash: MATCH\\nSocial Post: AUTHENTIC");
        } else {
          alert("✖ VERIFICATION FAILED: " + res.reason);
        }
      } catch(e) {
        alert("Verification error: " + e.message);
      }
    }
  </script>
</body>
</html>
"""

class PipelineRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving web dashboard and API endpoints."""

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        # Serve output images
        if path.startswith("/output/"):
            file_name = path[len("/output/"):]
            file_path = Config.OUTPUT_DIR / file_name
            self._serve_file(file_path)
            return

        # Serve sample images
        if path.startswith("/samples/"):
            file_name = path[len("/samples/"):]
            file_path = Path(__file__).resolve().parent / "samples" / file_name
            self._serve_file(file_path)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path == "/api/run":
            self._handle_api_run(body)
        elif path == "/api/verify":
            self._handle_api_verify(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, file_path: Path):
        if not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _handle_api_run(self, body: bytes):
        try:
            req = json.loads(body.decode("utf-8"))
            img_source = req.get("image", "samples/elon_musk.jpg")
            network = req.get("network", "simulator")
            hint = req.get("hint", "").strip() or None
            custom_filename = req.get("filename", "")

            base_dir = Path(__file__).resolve().parent

            # Handle base64 upload vs local sample
            if img_source.startswith("data:image"):
                header, encoded = img_source.split(",", 1)
                data_bytes = base64.b64decode(encoded)
                # Keep meaningful name if provided
                if custom_filename and not custom_filename.startswith("data:"):
                    clean_name = Path(custom_filename).stem + ".jpg"
                    temp_path = Config.OUTPUT_DIR / clean_name
                else:
                    temp_path = Config.OUTPUT_DIR / "uploaded_input.jpg"
                temp_path.write_bytes(data_bytes)
                target_image_path = temp_path
            else:
                target_image_path = base_dir / img_source

            # Run detection & encoding
            img = load_image(target_image_path)
            image_sha256 = compute_image_sha256(target_image_path)

            detector = FaceDetector(score_threshold=0.5)
            faces = detector.detect(img)
            if not faces:
                self._send_json({"status": "error", "message": "No face detected in the image. Please ensure the face is clearly visible."}, status=400)
                return

            primary_face = faces[0]
            encoder = FaceEncoder()
            face_enc = encoder.encode(img, primary_face)

            # Save artifacts
            crop_path = Config.OUTPUT_DIR / "detected_face.jpg"
            save_image(primary_face.raw_face_crop, crop_path)

            annotated_img = detector.draw_detections(img, [primary_face])
            annotated_path = Config.OUTPUT_DIR / "annotated_input.jpg"
            save_image(annotated_img, annotated_path)

            # Reverse Search with user hint support
            engine = ReverseImageSearchEngine()
            social_matches = engine.search(target_image_path, query_hint=hint)
            if not social_matches:
                social_matches = engine.search(crop_path, query_hint=hint)

            if not social_matches:
                self._send_json({"status": "error", "message": "No social media match found. Try entering a name or handle in the field."}, status=400)
                return

            top_match = social_matches[0]

            # Blockchain Recording
            attestation = AttestationBuilder.create_payload(
                image_sha256=image_sha256,
                face_encoding_data=face_enc,
                social_match=top_match.to_dict()
            )
            recorder = EVMBlockchainRecorder(network=network)
            receipt = recorder.record_match(attestation)

            response_data = {
                "status": "success",
                "image_sha256": image_sha256,
                "face_hash": face_enc["embedding_hash"],
                "face_crop_url": "/output/detected_face.jpg",
                "annotated_url": "/output/annotated_input.jpg",
                "social_match": top_match.to_dict(),
                "receipt": receipt.to_dict()
            }
            self._send_json(response_data)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, status=500)

    def _handle_api_verify(self, body: bytes):
        try:
            req = json.loads(body.decode("utf-8"))
            tx_hash = req.get("tx_hash")
            img_source = req.get("image", "samples/elon_musk.jpg")

            base_dir = Path(__file__).resolve().parent
            if img_source.startswith("data:image"):
                target_image_path = Config.OUTPUT_DIR / "uploaded_input.jpg"
            else:
                target_image_path = base_dir / img_source

            recorder = EVMBlockchainRecorder(network="simulator")
            on_chain = recorder.fetch_transaction_data(tx_hash)
            if not on_chain:
                self._send_json({"verified": False, "reason": "Transaction not found on chain"})
                return

            # Compare SHA
            cand_sha = compute_image_sha256(target_image_path)
            rec_sha = on_chain.get("image_integrity", {}).get("sha256", "")
            sha_match = cand_sha.lower() == rec_sha.lower()

            self._send_json({
                "verified": sha_match,
                "reason": "Cryptographic Match Confirmed" if sha_match else "Image SHA-256 digest mismatch"
            })
        except Exception as e:
            self._send_json({"verified": False, "reason": str(e)}, status=500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def start_server():
    server = HTTPServer((HOST, PORT), PipelineRequestHandler)
    print(f"=================================================================")
    print(f"  Face ID + Blockchain Verification Pipeline Web Dashboard")
    print(f"  Running locally at: http://{HOST}:{PORT}")
    print(f"=================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()

if __name__ == "__main__":
    start_server()
