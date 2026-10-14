from .mock import MockProvider
from .qwen_local import QwenLocalProvider
from .nano_banana import NanoBananaProvider
from ..config import settings

SUPPORTED_PROVIDERS={"mock","qwen_local","nano_banana"}

def get_provider(name: str):
    if name == "mock": return MockProvider()
    if name == "qwen_local": return QwenLocalProvider(settings.qwen_base_url, settings.qwen_model, settings.timeout_seconds)
    if name == "nano_banana": return NanoBananaProvider(settings.nano_banana_endpoint, settings.nano_banana_api_key, settings.timeout_seconds)
    raise ValueError("unsupported_provider")
