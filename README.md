# Street View Cleaner — Windows Local

A local Windows-only FastAPI application for removing Street View interface overlays while preserving real-world scene content. It runs on `localhost` and is controlled from a normal Windows browser; no iPad, cloud service, or external call is required when using the Mock or Qwen Local provider.

## What is included

- FastAPI backend with Pillow and OpenCV validation
- Four conservative heuristic UI zones: bottom-left map inset, top-left address label, bottom timeline, and bottom-right watermark
- Qwen Image Edit local HTTP adapter
- Nano Banana simple HTTP POST fallback adapter
- Mock provider for safe offline testing
- Resolution, corruption, structural-integrity, protected-edge, and hallucination guardrails
- Batch stop when manual-review/failure ratio exceeds 20%
- Atomic writes and unified logging
- Windows browser UI with Run Batch, preview grid, compare slider, Re-run, ZIP download, and provider selector

## Windows installation

Open **PowerShell** in this folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
Copy-Item .env.template .env
```

If PowerShell blocks activation for the current user, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Safe local smoke test

The Mock provider returns the original image and exercises the full API, validation, preview, manifest, and ZIP flow without model weights or credentials.

```powershell
$env:DEFAULT_PROVIDER="mock"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> in a Windows browser and select **Mock (safe test)**.

## Provider configuration

Edit `.env`:

- `DEFAULT_PROVIDER=mock`, `qwen_local`, or `nano_banana`
- `QWEN_BASE_URL` points to the local Qwen Image Edit HTTP service
- `QWEN_MODEL` defaults to `Qwen/Qwen-Image-Edit-2511`
- `NANO_BANANA_ENDPOINT` and `NANO_BANANA_API_KEY` configure the optional remote provider
- `MODEL_PATH` records a local model path for the Qwen service; the service itself owns model loading

The browser cannot submit arbitrary instructions. Presets are server-owned. Low and medium UI confidence always use **Preserve Scene**.

## Run tests

```powershell
python -m pytest -q
```

The test suite covers preset safety, OpenCV fail-safes, provider routing, API static serving, upload/process/export, and ZIP integrity.

## Optional Docker on Windows

Docker Desktop users can run:

```powershell
docker compose up --build
```

The application remains local-first; do not expose port 8000 publicly without adding authentication and TLS.

## Foundation

The Qwen adapter follows the official Qwen Image Edit project:
<https://github.com/QwenLM/Qwen-Image>

Model weights and provider credentials are intentionally not included in this ZIP.

## Architecture and Instagram Cleaner Mode

The provider factory is isolated from HTTP routing. The pipeline uses a provider-edit strategy that accepts either normalized bounding-box regions or a 2D image mask, so heuristic and future AI detections share one validation contract.

Uploads are read through bounded spooled temporary buffers and closed automatically. Outputs and state files are written atomically. The production Docker runtime uses four Uvicorn workers and persists job state/manifests under `STORAGE_ROOT` so status and reruns do not depend exclusively on one worker's memory.

Select **Instagram Cleaner Mode** to use the Instagram profile. It detects conservative candidate zones for the top navigation bar, story tray, post interaction overlays, and bottom action icons. The mode uses a dedicated preserve-scene instruction and exposes an OpenCV Telea masking/patch helper; uncertain boundaries remain fail-closed.

## Architecture alert resolution

`backend/app/providers/router.py` contains no FastAPI decorators or endpoint handling; it is only a backward-compatible provider-factory shim. All HTTP routes remain in `backend/app/main.py`.

The application now includes a WAL-backed SQLite state cache and durable queue metadata at `storage/state/street_view_cleaner.sqlite3`. Job status, provider/preset options, and result metadata are persisted so multi-worker requests can read state consistently. Uploaded bytes are not retained in process memory for reruns; reruns reload originals from the job's disk-backed original directory.

## Native Instagram Strategy

`InstagramCleaningStrategy` is registered directly by the `instagram_screenshot_cleaner` preset. Its exact normalized coordinate rules cover the top navigation title banner, story tray rings, post engagement overlay, and bottom application menu dock. The strategy converts those rules to pixel bounding boxes, exposes a binary mask, and provides an optional OpenCV Telea patch helper. The frontend sends both `preset` and `mode` so Instagram selection reaches the backend explicitly.

## Live Provider Configuration

The live adapters are configured through the local `.env` file; credentials are never committed.

```env
DEFAULT_PROVIDER=qwen_local
QWEN_BASE_URL=http://127.0.0.1:8188
QWEN_EDIT_PATH=/v1/images/edits
QWEN_MODEL=Qwen/Qwen-Image-Edit-2511
NANO_BANANA_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent
NANO_BANANA_API_KEY=replace-locally
GOOGLE_VISION_ENABLED=false
GOOGLE_APPLICATION_CREDENTIALS=C:\\Users\\<user>\\.gcp\\street-view-vision.json
```

Qwen Local is attempted first when selected. The existing provider fallback order then tries Nano Banana and Qwen Local as configured. Google Cloud Vision OCR is optional and disabled by default; enable it only after installing the `vision` dependency and placing a service-account JSON file at the local path. OCR only contributes likely UI text bounding boxes and does not edit images.
