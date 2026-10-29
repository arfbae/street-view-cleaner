from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

from .config import settings
from .logging_module import logger

UI_TERMS = {
    "instagram": {"like", "comment", "share", "follow", "home", "reels", "profile", "message", "send"},
    "street_view": {"street view", "maps", "pegman", "zoom", "compass", "satellite", "directions"},
}


def _likely_ui_text(text: str, profile: str) -> bool:
    value = " ".join(text.lower().split())
    return any(term in value for term in UI_TERMS.get(profile, set()))


def _detect_sync(image_bytes: bytes, profile: str):
    try:
        from google.cloud import vision
    except ImportError:
        logger.warning("Google Vision is enabled but google-cloud-vision is not installed")
        return []

    credentials = None
    if settings.google_application_credentials:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            str(Path(settings.google_application_credentials).expanduser())
        )

    client = vision.ImageAnnotatorClient(credentials=credentials)
    response = client.text_detection(image=vision.Image(content=image_bytes))
    error = getattr(response, "error", None)
    if error is not None and getattr(error, "message", None):
        raise RuntimeError(error.message)

    text_annotations = getattr(response, "text_annotations", None) or []
    if not text_annotations:
        return []

    image = Image.open(__import__("io").BytesIO(image_bytes))
    width, height = image.size
    regions = []
    for annotation in text_annotations[1:]:
        text = annotation.description or ""
        if not _likely_ui_text(text, profile):
            continue
        vertices = annotation.bounding_poly.vertices
        xs = [max(0, min(width, v.x or 0)) for v in vertices]
        ys = [max(0, min(height, v.y or 0)) for v in vertices]
        if xs and ys:
            regions.append({
                "name": "google_vision_ui_text",
                "box": [min(xs), min(ys), max(xs), max(ys)],
                "confidence": 0.70,
                "profile": profile,
                "text": text,
            })
    return regions


async def detect_ui_text(image_bytes: bytes, profile: str):
    if not settings.google_vision_enabled:
        return []
    try:
        return await asyncio.to_thread(_detect_sync, image_bytes, profile)
    except Exception as exc:
        logger.warning("Google Vision OCR unavailable: %s", type(exc).__name__)
        return []
