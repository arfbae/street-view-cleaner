import argparse
import json
import uuid
import zipfile
from pathlib import Path

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .image_io import read_stream, save_bytes
from .pipeline import process_job
from .state_store import store

app = FastAPI(title=settings.app_name, version="1.1.0")
frontend_dir = Path(__file__).parents[2] / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
JOBS = {}
ALLOWED_PROVIDERS = {"mock", "qwen_local", "nano_banana"}
ALLOWED_PRESETS = {
    "clean_mode",
    "preserve_scene",
    "keep_sky",
    "keep_edges",
    "soft_rebuild",
    "instagram_screenshot_cleaner",
}
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _state_path(job_id):
    return Path(settings.storage_root) / job_id / "state.json"


def _start_job(job_id, items, provider_name, preset):
    JOBS[job_id] = {"status": "processing", "results": []}
    store.set(job_id, "processing", provider_name, preset, {"results": []})
    _state_path(job_id).parent.mkdir(parents=True, exist_ok=True)
    save_bytes(
        _state_path(job_id),
        json.dumps({
            "job_id": job_id,
            "status": "processing",
            "provider": provider_name,
            "preset": preset,
        }).encode(),
    )

    async def run():
        results, status = await process_job(job_id, items, provider_name, preset)
        JOBS[job_id] = {"status": status, "results": results}
        store.set(job_id, status, provider_name, preset, {"results": results})
        save_bytes(
            _state_path(job_id),
            json.dumps({
                "job_id": job_id,
                "status": status,
                "provider": provider_name,
                "preset": preset,
            }).encode(),
        )

    return run


@app.get("/", response_class=HTMLResponse)
def index():
    return (frontend_dir / "index.html").read_text(encoding="utf-8")


@app.post("/set_model_provider")
async def set_model_provider(provider: str = Form(...)):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(400, "unsupported_provider")
    try:
        settings.validate_provider_settings(provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    settings.default_provider = provider
    return {"status": "ok", "provider": provider}


@app.get("/healthz")
def health():
    return {"status": "ok", "provider": settings.default_provider}


@app.get("/api/v1/config")
def config():
    return {
        "providers": sorted(ALLOWED_PROVIDERS),
        "default_provider": settings.default_provider,
        "presets": sorted(ALLOWED_PRESETS),
        "platform": "Windows localhost",
    }


@app.post("/api/v1/jobs", status_code=202)
async def create_job(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    provider: str | None = Form(None),
    preset: str | None = Form(None),
    mode: str | None = Form(None),
):
    if len(files) > 100:
        raise HTTPException(413, "too_many_files")
    provider_name = provider or settings.default_provider
    if provider_name not in ALLOWED_PROVIDERS:
        raise HTTPException(400, "unsupported_provider")
    try:
        settings.validate_provider_settings(provider_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    effective_preset = mode or preset
    if effective_preset and effective_preset not in ALLOWED_PRESETS:
        raise HTTPException(400, "unsupported_preset")
    items = []
    for upload in files:
        filename = Path(upload.filename or "upload").name
        if filename.rsplit(".", 1)[-1].lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, "unsupported_format")
        try:
            data = read_stream(upload.file, settings.max_upload_bytes)
        except ValueError as exc:
            raise HTTPException(413, str(exc))
        items.append((filename, data))
    job_id = uuid.uuid4().hex
    store.enqueue(job_id, provider_name, effective_preset)
    background.add_task(_start_job(job_id, items, provider_name, effective_preset))
    return {"job_id": job_id, "status": "queued", "item_count": len(items)}


@app.post("/api/v1/jobs/{job_id}/rerun", status_code=202)
async def rerun_job(job_id: str, background: BackgroundTasks):
    state_path = _state_path(job_id)
    manifest = Path(settings.storage_root) / job_id / "manifest.json"
    db_state = store.get(job_id)
    if not state_path.exists() or not manifest.exists():
        raise HTTPException(404, "job_not_rerunnable")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    items = []
    if db_state:
        state["provider"] = db_state.get("provider") or state.get("provider")
        state["preset"] = db_state.get("preset") or state.get("preset")
    for item in payload.get("results", []):
        matches = list((manifest.parent / "original").glob(f"{item['item_id']}_*"))
        if matches:
            items.append((item.get("filename", matches[0].name), matches[0].read_bytes()))
    provider_name, preset = state.get("provider", settings.default_provider), state.get("preset")
    background.add_task(_start_job(job_id, items, provider_name, preset))
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    if job_id in JOBS:
        return {"job_id": job_id, **JOBS[job_id]}
    db_state = store.get(job_id)
    manifest = Path(settings.storage_root) / job_id / "manifest.json"
    state = _state_path(job_id)
    if manifest.exists():
        return json.loads(manifest.read_text(encoding="utf-8"))
    if db_state:
        return {
            "job_id": job_id,
            "status": db_state["status"],
            "provider": db_state.get("provider"),
            "preset": db_state.get("preset"),
            "results": db_state.get("payload", {}).get("results", []),
        }
    if state.exists():
        return json.loads(state.read_text(encoding="utf-8"))
    raise HTTPException(404, "job_not_found")


def _item_output(job_id, item_id, original=False):
    manifest = Path(settings.storage_root) / job_id / "manifest.json"
    if not manifest.exists():
        raise HTTPException(404, "job_not_found")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    item = next((x for x in data.get("results", []) if x.get("item_id") == item_id), None)
    if not item:
        raise HTTPException(404, "item_not_found")
    if original:
        matches = list((manifest.parent / "original").glob(f"{item_id}_*"))
        path = matches[0] if matches else None
    else:
        path = Path(item["output"]) if item.get("output") else None
    if not path or not path.exists():
        raise HTTPException(409, "image_unavailable")
    return FileResponse(path)


@app.get("/api/v1/jobs/{job_id}/items/{item_id}/original")
def original_image(job_id: str, item_id: str):
    return _item_output(job_id, item_id, True)


@app.get("/api/v1/jobs/{job_id}/items/{item_id}/output")
def output_image(job_id: str, item_id: str):
    return _item_output(job_id, item_id, False)


@app.get("/api/v1/jobs/{job_id}/download.zip")
def download(job_id: str):
    job = Path(settings.storage_root) / job_id
    manifest = job / "manifest.json"
    if not manifest.exists():
        raise HTTPException(409, "job_incomplete")
    zpath = job.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest, "manifest.json")
        for item in (job / "output").glob("*.png"):
            archive.write(item, "output/" + item.name)
    return FileResponse(zpath, media_type="application/zip", filename=f"{job_id}.zip")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Street View Cleaner web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development.")
    args = parser.parse_args(argv)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
