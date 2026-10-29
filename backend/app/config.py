from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "street-view-cleaner"
    default_provider: str = "mock"
    qwen_base_url: str = ""
    qwen_model: str = "Qwen/Qwen-Image-Edit-2511"
    qwen_edit_path: str = "/v1/images/edits"
    nano_banana_endpoint: str = ""
    nano_banana_api_key: str = ""
    timeout_seconds: int = 30
    retry_count: int = 1
    max_batch_failure_ratio: float = 0.20
    structural_diff_threshold: float = 0.15
    max_upload_bytes: int = 25_000_000
    storage_root: Path = BASE_DIR / "storage"
    model_path: str = ""
    google_vision_enabled: bool = False
    google_application_credentials: str = ""
    google_vision_project: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_provider_settings(self, provider_name: str | None = None) -> str:
        provider = (provider_name or self.default_provider or "mock").strip()
        if provider == "qwen_local" and not self.qwen_base_url:
            raise ValueError("QWEN_BASE_URL is required when qwen_local is selected")
        if provider == "nano_banana" and (not self.nano_banana_endpoint or not self.nano_banana_api_key):
            raise ValueError("NANO_BANANA_ENDPOINT and NANO_BANANA_API_KEY are required when nano_banana is selected")
        return provider


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
