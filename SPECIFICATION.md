# Street View Screenshot Cleaner
## Minimal Production Specification

**Status:** Production-ready design specification  
**Primary goal:** Remove Street View interface elements from screenshots through instruction-based image editing while preserving all real-world scene content.  
**Control surface:** Responsive web UI optimized for iPad Safari.  
**Initial providers:** Qwen Local and Nano Banana.

---

## 1. System Overview

The system accepts one or more Street View screenshots, detects visible interface/UI regions, sends the image with a hardened editing instruction to the selected image model, validates the result against the original, and returns approved cleaned images or items marked for manual review.

### Non-negotiable behavior

1. **Remove UI only:** Remove controls, navigation overlays, attribution panels, watermarks, compass/zoom controls, and other clearly identified interface elements.
2. **Preserve the scene:** Do not remove, invent, move, repaint, or materially alter buildings, roads, vehicles, people, trees, poles, fences, bins, signs, sky, shadows, or other real-world objects.
3. **Fail closed:** An uncertain, invalid, structurally changed, or hallucinated result is never silently accepted.
4. **Keep it simple:** One backend service, one lightweight frontend, two provider adapters, locked presets, and deterministic validation.

### Inputs and outputs

- **Inputs:** PNG, JPEG, or WebP screenshots; one image or a batch.
- **Outputs:** Cleaned image, original image reference, processing status, provider used, validation results, and optional manual-review reason.
- **Output package:** ZIP containing approved outputs and a machine-readable `manifest.json`.

---

## 2. Architecture

```text
[iPad Web UI]
      |
      | HTTPS/JSON + multipart upload
      v
[FastAPI API]
      |
      +--> [Job/Batch Controller]
      |          |
      |          +--> [UI Detector]
      |          +--> [Preset Selector]
      |          +--> [Provider Router]
      |                         |
      |                         +--> [Qwen Local Adapter]
      |                         +--> [Nano Banana Adapter]
      |          |
      |          +--> [Image Validator]
      |          +--> [Structural Guardrails]
      |          +--> [Output Writer]
      |
      +--> [Local/Attached Storage]
```

### Deployment shape

- One containerized FastAPI application.
- One persistent storage volume for inputs, outputs, temporary files, and manifests.
- Qwen Local reachable through a local model service or configured internal endpoint.
- Nano Banana reachable through its authenticated provider API.
- HTTPS required outside localhost.
- No database is required for the first production version; job state may be stored as JSON files keyed by job ID. A database can be added later without changing the API contract.

### Runtime configuration

Configuration is loaded from environment variables or a mounted configuration file, never hard-coded in request handlers.

```text
INPUT_DIR=input
OUTPUT_DIR=output
ZIP_DIR=zips
DEFAULT_PROVIDER=qwen_local
TIMEOUT_SECONDS=30
RETRY_COUNT=1
MAX_BATCH_FAILURE_RATIO=0.20
STRUCTURAL_DIFF_THRESHOLD=0.15
MAX_UPLOAD_BYTES=<deployment limit>
```

---

## 3. Backend Layout

```text
backend/
├── app/
│   ├── main.py                 # FastAPI application and startup
│   ├── config.py               # Environment-backed settings
│   ├── schemas.py              # Request/response models
│   ├── api.py                  # HTTP routes
│   ├── pipeline.py             # Single and batch orchestration
│   ├── detector.py             # Street View UI detection
│   ├── presets.py              # Locked editing instructions
│   ├── providers/
│   │   ├── base.py             # Common provider interface
│   │   ├── qwen_local.py       # Qwen adapter
│   │   └── nano_banana.py      # Nano Banana adapter
│   ├── validation/
│   │   ├── image.py            # Decode, blank, corruption, resolution checks
│   │   ├── structure.py         # Protected-region comparison
│   │   └── hallucination.py     # New-object detection
│   ├── storage.py               # Safe paths, writes, ZIP creation, manifests
│   └── errors.py                # Typed errors and safe public messages
├── tests/
│   ├── test_api.py
│   ├── test_pipeline.py
│   ├── test_presets.py
│   └── fixtures/
├── Dockerfile
└── pyproject.toml
```

### Module responsibilities

- **`config`:** Validates settings at startup and exposes immutable runtime configuration.
- **`presets`:** Stores versioned, locked-down instructions; clients may select a preset ID but may not submit arbitrary model instructions.
- **`detector`:** Locates likely UI regions and returns a confidence score plus masks.
- **`providers`:** Normalizes Qwen and Nano Banana into one interface with timeout, retry, and provider-specific error handling.
- **`validation`:** Rejects corrupt, blank, resized, structurally changed, or hallucinated outputs.
- **`pipeline`:** Applies detection, instruction selection, provider fallback, validation, and result recording.
- **`storage`:** Prevents path traversal, isolates jobs, and writes outputs atomically.
- **`api`:** Exposes only the public HTTP contract; it does not contain model or validation logic.

---

## 4. Frontend Layout

The frontend is a responsive single-page web UI designed for touch use on iPad Safari.

### Views

1. **Upload:** Drag/drop on desktop and photo picker on iPad; supports one or multiple images.
2. **Settings:** Provider selector, preset selector, and optional batch mode. Only allowed values are shown.
3. **Progress:** Job status, per-image progress, provider used, retry count, and validation state.
4. **Review:** Before/after comparison with swipe or side-by-side view; manual-review items are clearly separated.
5. **Export:** Download individual approved images or the validated ZIP package.

### iPad requirements

- Responsive layout with touch targets at least 44 CSS pixels.
- No hover-only controls.
- Safari-compatible file upload and download.
- Portrait and landscape layouts.
- Persistent job status through polling; do not depend on a long-lived browser connection.
- Keep original and cleaned images available for comparison.
- Do not expose filesystem paths, provider credentials, or raw internal errors.

### Minimal frontend API client

```text
POST /api/v1/jobs                 create a single or batch job
GET  /api/v1/jobs/{job_id}        read job and item status
GET  /api/v1/jobs/{job_id}/items/{item_id}/original
GET  /api/v1/jobs/{job_id}/items/{item_id}/output
GET  /api/v1/jobs/{job_id}/download.zip
GET  /api/v1/config               read allowed providers and presets
```

---

## 5. API Endpoints

All endpoints are under `/api/v1`, return JSON except image and ZIP downloads, and require HTTPS in deployed environments.

### `GET /healthz`

Returns service health and version. It must not expose credentials or provider secrets.

### `GET /api/v1/config`

Returns enabled providers, default provider, available preset IDs, upload limits, and supported formats.

### `POST /api/v1/jobs`

Creates a processing job.

- **Content type:** `multipart/form-data`
- **Fields:** `files[]`, `provider` (`qwen_local` or `nano_banana`), `preset` (allowed preset ID)
- **Response:** `202 Accepted`

```json
{
  "job_id": "job_123",
  "status": "queued",
  "item_count": 4
}
```

The server generates job and item IDs. Client-supplied paths are never accepted.

### `GET /api/v1/jobs/{job_id}`

Returns overall status and item-level results.

```json
{
  "job_id": "job_123",
  "status": "completed",
  "results": [
    {
      "item_id": "item_001",
      "status": "ok",
      "provider": "qwen_local",
      "preset": "clean_mode",
      "ui_confidence": 0.96,
      "validation": {"resolution": true, "structure": true, "hallucination": true}
    }
  ]
}
```

Possible item statuses: `queued`, `processing`, `ok`, `manual_review`, `failed`.

### `GET /api/v1/jobs/{job_id}/items/{item_id}/original`

Streams the original uploaded image after authorization and job ownership checks.

### `GET /api/v1/jobs/{job_id}/items/{item_id}/output`

Streams an approved cleaned image. Returns `409` if the item is not approved.

### `GET /api/v1/jobs/{job_id}/download.zip`

Streams a ZIP containing only approved outputs and `manifest.json`. Returns `409` while the job is incomplete.

### `POST /api/v1/settings/provider`

Changes the default provider for subsequent jobs. This is an application setting, not per-request mutable global state.

```json
{"provider": "nano_banana"}
```

The endpoint validates the provider, persists the setting safely, and returns the new value. Existing jobs are unaffected.

### Error contract

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "The image requires manual review.",
    "request_id": "req_123"
  }
}
```

Public errors are stable and non-sensitive; detailed provider errors are logged server-side with secrets removed.

---

## 6. Model Provider Switch: Qwen + Nano Banana

Both providers implement the same interface:

```text
edit(image_bytes, instruction, timeout_seconds) -> image_bytes | ProviderError
```

### Routing rules

1. Use the job-selected provider, or the configured default.
2. Retry the selected provider once on transient failure or invalid output.
3. Fall back to the other enabled provider once.
4. Re-run with the stricter `preserve_scene` preset when validation fails.
5. Mark `manual_review` if no valid result passes all checks.

### Provider roles

- **Qwen Local:** Default for privacy, predictable local operation, and lower external dependency.
- **Nano Banana:** Fallback or explicitly selected provider for cases where its image-editing behavior is preferred.

Provider adapters must normalize dimensions, MIME type, errors, timeouts, and output bytes. Provider credentials and endpoints are configuration-only. The frontend never calls a provider directly.

---

## 7. Hardened Presets

Presets are versioned server-side and are not editable from the UI. Each instruction must state that the source image is authoritative and that only detected interface pixels may change.

### `clean_mode`

> Remove only clearly identified Street View interface overlays and controls inside the supplied UI mask. Reconstruct only the immediately adjacent background pixels needed to close those UI regions. Preserve every real-world object, texture, edge, sign, person, vehicle, building, vegetation element, pole, fence, bin, road marking, shadow, reflection, sky feature, and perspective relationship. Do not add, remove, move, sharpen into existence, or redesign any scene content. If the UI boundary is uncertain, make no edit and request manual review.

### `preserve_scene`

> Make the smallest possible edit. Remove only the explicitly detected Street View UI pixels. Preserve all scene content exactly, including objects partly covered by UI. Do not infer or invent hidden objects. If a safe reconstruction is not possible, return the original image or signal manual review rather than guessing.

### `keep_sky`

> Apply the preserve-scene instruction and never alter sky gradients, clouds, sun, haze, or horizon geometry except for pixels directly occupied by confirmed UI.

### `keep_edges`

> Apply the preserve-scene instruction and protect building edges, fence lines, poles, tree trunks, road boundaries, signs, and other high-contrast boundaries from alteration.

### `soft_rebuild`

> Use only after a confirmed UI mask and only for a narrow adjacent background region. Rebuild with local texture, color, lighting, and perspective continuity. Do not reconstruct objects or extend geometry. Abort if the region contains uncertain scene content.

The effective instruction is composed from one primary preset plus applicable protection clauses. Arbitrary user text is not passed to the model in the first production version.

---

## 8. Automatic UI Detection

`detect_ui(image)` returns:

```text
{
  mask: binary or polygon mask,
  confidence: 0.0–1.0,
  regions: [region_type, bounds, confidence]
}
```

### Detection strategy

1. Detect known Street View UI patterns by position, shape, color, and text/icon characteristics.
2. Combine template or computer-vision rules with an optional lightweight detector.
3. Exclude regions that overlap likely real-world objects unless UI confidence is high.
4. Use thresholds:
   - `high`: apply `clean_mode`.
   - `medium`: apply `preserve_scene` with a narrow mask.
   - `low`: do not automatically edit; mark for manual review.

The detector must be conservative. A missed UI region is safer than an incorrect edit to a real-world object.

---

## 9. Data Flow

### Single image

1. Upload image and validate MIME type, size, dimensions, and decodeability.
2. Store it under a generated job/item directory; never use the original filename as a path.
3. Compute a checksum and record metadata.
4. Detect UI regions and confidence.
5. Select a locked preset.
6. Call the selected provider with timeout and retry.
7. Validate output bytes and dimensions.
8. Run protected-region structural checks.
9. Run new-object/hallucination checks.
10. If any check fails, retry with `preserve_scene` and provider fallback once.
11. Save approved output atomically, or mark `manual_review`.
12. Update the item manifest and job status.

### Batch

Process items independently, record every result, and stop starting new items when the ratio of `manual_review` or fatal failures exceeds `MAX_BATCH_FAILURE_RATIO` (default 20%). Already completed approved items remain available. The final ZIP includes only approved outputs.

---

## 10. Validation and Fail-Safes

- **Image validity:** Reject missing, blank, corrupted, unsupported, or oversized output.
- **Resolution check:** Output dimensions must match the original unless a configured lossless format conversion is required.
- **Protected-region check:** Compare masked regions containing fence lines, poles, bins, tree trunks, building edges, signs, roads, and other detected scene structures. Reject changes above the configured threshold.
- **Hallucination check:** Detect new objects or material object changes not present in the original. Reject on positive detection or low confidence.
- **Mask containment:** Any changed pixels must be inside the UI mask or its tightly bounded reconstruction margin.
- **Original retention:** Never overwrite the uploaded original.
- **Atomic output:** Write to a temporary file, validate it, then rename into the approved output location.
- **Auditability:** Store provider, preset version, detector confidence, validation results, timestamps, and error code in the manifest.

Manual review is the safe outcome for ambiguity; it is not a model failure to be hidden.

---

## 11. Constraints and Security

### Product constraints

- UI removal only; no general photo retouching.
- No object removal, replacement, enhancement, upscaling, or creative reconstruction.
- No automatic crop unless explicitly added as a separate, user-visible feature.
- No arbitrary model prompts in the initial release.
- No more than one provider fallback and one stricter-preset retry per item.

### Operational constraints

- Enforce upload count, file size, pixel dimensions, timeout, and batch limits.
- Use bounded concurrency to protect local model and host resources.
- Expire temporary files and job manifests according to a configurable retention period.
- Log request IDs and job IDs, but never log image bytes, credentials, or full prompts containing sensitive data.
- Add health checks for storage and each enabled provider.
- Require authentication or network protection before exposing the service beyond a trusted private network.

### Security constraints

- Reject path traversal and client-provided filesystem paths.
- Allowlist MIME types and decode formats.
- Use authenticated provider secrets from environment/configuration storage.
- Apply request size limits and rate limits.
- Restrict CORS to the deployed iPad UI origin.
- Return generic errors to clients and detailed sanitized errors only to server logs.

---

## 12. Acceptance Criteria

The first production release is acceptable when:

- A user can upload one or many screenshots from an iPad.
- The user can select Qwen Local or Nano Banana without changing the UI.
- The system detects likely UI conservatively and selects a hardened preset.
- Approved results preserve dimensions and protected scene structure.
- Invalid or uncertain results become `manual_review`, never silent success.
- Provider timeout, retry, and fallback behavior is bounded and observable.
- Batch processing stops safely above the configured failure ratio.
- The iPad UI can monitor jobs and download approved images or a ZIP.
- No client can supply a filesystem path or arbitrary editing instruction.
- A manifest explains how every output was produced and validated.

---

## 13. Final Summary

Build one small FastAPI service with five practical concerns: configuration, presets, provider adapters, validation/fail-safes, and pipeline/API orchestration. Use conservative automatic UI detection, locked instruction presets, Qwen Local as the default provider, Nano Banana as the selectable fallback, and a fail-closed validation path. Provide a responsive iPad web UI for upload, progress, review, and export. The defining product rule is simple: **change only confirmed Street View UI pixels; preserve the real-world scene; otherwise require manual review.**


## Improvement Addendum (Integrated)

- Windows local-first deployment with LAN access for iPad Safari.
- Explicit heuristic UI zones: bottom-left map inset, top-left address label, bottom timeline, and bottom-right watermark.
- Low and medium confidence remain conservative and use Preserve Scene.
- Batch processing stops when manual-review/failure ratio exceeds the configured 20% threshold.
- Frontend now has separated `styles.css`, `app.js`, and `compare.js` assets, plus a Re-run control.
- Added unified logging, atomic image writes, a fail-safe module, and an `.env.template` alias.
- Added `/set_model_provider` compatibility endpoint while retaining the versioned API.

## Final Implementation (Windows)

Version 1.0 is implemented for Windows localhost use with Python 3.11, FastAPI, Pillow, OpenCV, and a standard Windows browser.

- **Backend:** `backend/app` contains configuration, API/job lifecycle, pipeline, provider adapters, image I/O, UI detection, logging, validation, and fail-safes.
- **Providers:** Mock is offline-safe; Qwen Local uses a configurable local HTTP image-edit endpoint following the Qwen Image Edit request model; Nano Banana uses a configurable HTTP POST wrapper.
- **Detection:** Four heuristic zones are returned for the bottom-left map inset, top-left address label, bottom timeline, and bottom-right watermark. Confidence is 0.50 until a stronger detector is installed.
- **Safety:** Low and medium confidence always select `preserve_scene`. Every output passes corruption, resolution, OpenCV structural-integrity, protected-edge, and possible-new-object checks. Failures become `manual_review`.
- **Batching:** Processing stops when the ratio of `manual_review` or failed items exceeds `MAX_BATCH_FAILURE_RATIO` (default 20%).
- **Frontend:** The Windows browser UI supports Run Batch, preview grid, original/cleaned compare slider, Re-run, ZIP download, and provider selection.
- **Storage:** Originals are retained, outputs are atomically written, and each job receives a manifest and ZIP export.
- **Run command:** `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.

## Architectural Refactor and Instagram Integration

### Phase 1: Stabilization

- Provider construction is isolated in `providers/factory.py`; `providers/router.py` is a compatibility shim and contains no HTTP handling.
- `edit_strategies.py` defines the provider-independent Strategy boundary. The pipeline accepts either region bounding boxes or a 2D mask uniformly and passes the same normalized regions to validation.
- `image_io.py` uses bounded `SpooledTemporaryFile` upload reads, context-managed Pillow buffers, and atomic replacement writes with cleanup.
- Docker and Compose run Uvicorn with four workers. Job state and manifests persist under the storage root so multi-worker status reads and reruns remain recoverable.

### Phase 2: Instagram Screenshot Cleaner

- `ui_detection.py` supports `street_view` and `instagram` profiles.
- Instagram candidate zones are `top_navigation_bar`, `story_tray`, `post_interaction_overlay`, and `bottom_action_icons`.
- `patch_ui_regions()` provides an OpenCV Telea inpainting helper for explicitly selected masks; the normal model path remains validated and fail-closed.
- `instagram_screenshot_cleaner` is a server-owned preset and is selectable from the frontend.
- The existing design system is preserved while the selector routes the selected preset through the same batch pipeline.

## Architecture Alert Verification

- Route scan confirms all FastAPI decorators are in `backend/app/main.py`; `providers/router.py` has no HTTP route declarations and only re-exports the provider factory.
- `state_store.py` provides a WAL-backed SQLite state cache and durable queue metadata under `storage/state/`.
- Upload streams use bounded spooled buffers, while reruns reload originals from disk rather than retaining upload bytes in process-local memory.
- `verify_imports.py` imports the critical package modules and confirms no circular import errors.

## Native Instagram Strategy Registration

`edit_strategies.py` now contains `InstagramCleaningStrategy`, a concrete implementation of the shared `EditStrategy` interface. `presets.py` maps `instagram_screenshot_cleaner` directly to that class through `STRATEGY_BY_PRESET`. The strategy defines exact normalized coordinate rules and produces pixel boxes and masks for the title banner, story rings, post engagement overlay, and bottom application menu dock. The API accepts the explicit `mode` field alongside `preset`, and the frontend sends both values.
