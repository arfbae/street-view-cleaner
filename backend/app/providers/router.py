"""Backward-compatible provider factory; HTTP routes do not belong here."""
from .factory import get_provider, SUPPORTED_PROVIDERS

def provider(name: str):
    return get_provider(name)
