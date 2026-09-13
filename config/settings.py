"""
Configuration Loader for Industrial Process Data Monitoring & Validation System.
Reads configuration from environment variables (.env) with sensible defaults.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application and PI Web API configuration settings."""
    
    # PI Web API Configuration
    PI_WEB_API_URL: str = os.getenv("PI_WEB_API_URL", "https://mock-pi-server.local/piwebapi").rstrip("/")
    PI_DATA_SERVER_NAME: str = os.getenv("PI_DATA_SERVER_NAME", "PIDATA01")
    PI_AUTH_MODE: str = os.getenv("PI_AUTH_MODE", "mock").lower()  # 'basic', 'windows', 'mock'
    PI_USERNAME: Optional[str] = os.getenv("PI_USERNAME", None)
    PI_PASSWORD: Optional[str] = os.getenv("PI_PASSWORD", None)
    PI_VERIFY_SSL: bool = os.getenv("PI_VERIFY_SSL", "false").lower() in ("true", "1", "yes")
    PI_TIMEOUT_SECONDS: int = int(os.getenv("PI_TIMEOUT_SECONDS", "10"))
    
    # Application & Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEFAULT_LOOKBACK_HOURS: int = int(os.getenv("DEFAULT_LOOKBACK_HOURS", "2"))
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CONFIG_DIR: Path = BASE_DIR / "config"
    TAGS_CONFIG_PATH: Path = CONFIG_DIR / "tags_config.json"
    SAMPLE_DATA_DIR: Path = BASE_DIR / "sample_data"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    
    @classmethod
    def is_mock_mode(cls) -> bool:
        """Returns True if the system is configured in offline simulation/mock mode."""
        return cls.PI_AUTH_MODE == "mock" or "mock-pi-server" in cls.PI_WEB_API_URL


settings = Settings()
