from __future__ import annotations

from io import BytesIO
from abc import ABC, abstractmethod
from typing import Any

from PIL import Image

from .providers.factory import get_provider
from .ui_detection import patch_ui_regions

RegionInput = list[dict[str, Any]] | Any | None


class EditStrategy(ABC):
    """Provider-independent editing boundary accepting boxes or masks."""

    @abstractmethod
    async def edit(self, image_bytes: bytes, instruction: str, regions: RegionInput = None) -> bytes: ...


async def _apply_region_guard(image_bytes: bytes, edited_bytes: bytes, regions: RegionInput) -> bytes:
    if not regions:
        return edited_bytes
    try:
        original = Image.open(BytesIO(image_bytes)).convert("RGB")
        output_image = Image.open(BytesIO(edited_bytes)).convert("RGB")
        if output_image.size != original.size:
            return edited_bytes
        patched = patch_ui_regions(output_image, regions, radius=3)
        buffer = BytesIO()
        patched.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return edited_bytes


class ProviderEditStrategy(EditStrategy):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    async def edit(self, image_bytes: bytes, instruction: str, regions: RegionInput = None) -> bytes:
        edited = await get_provider(self.provider_name).edit(image_bytes, instruction)
        return await _apply_region_guard(image_bytes, edited, regions)


class InstagramCleaningStrategy(ProviderEditStrategy):
    PROFILE = "instagram"
    COORDINATE_RULES = {
        "top_navigation_title_banner": (0.00, 0.00, 1.00, 0.12),
        "story_tray_rings": (0.00, 0.12, 1.00, 0.30),
        "post_engagement_overlay": (0.00, 0.70, 1.00, 0.88),
        "bottom_application_menu_dock": (0.00, 0.88, 1.00, 1.00),
    }

    def regions_for_image(self, image: Image.Image) -> list[dict[str, Any]]:
        width, height = image.size
        return [{
            "name": name,
            "box": [round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height)],
            "confidence": 0.50,
            "profile": self.PROFILE,
        } for name, (x1, y1, x2, y2) in self.COORDINATE_RULES.items()]


def strategy_for_preset(preset: str | None, provider_name: str) -> EditStrategy:
    return InstagramCleaningStrategy(provider_name) if preset == "instagram_screenshot_cleaner" else ProviderEditStrategy(provider_name)


def normalize_regions(regions: RegionInput) -> RegionInput:
    if regions is None or isinstance(regions, list):
        return regions
    if getattr(regions, "ndim", None) == 2:
        return regions
    raise TypeError("regions must be a list of boxes or a 2D mask")
