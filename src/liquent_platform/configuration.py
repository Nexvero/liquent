"""Fail-fast runtime configuration for Liquent process roles."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    CI = "ci"
    PREVIEW = "preview"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PlatformSettings(BaseSettings):
    """Validated settings shared by the initial platform processes.

    Secrets can be supplied as constructor values for isolated tests or through
    files in ``/run/secrets`` in containers. Unknown settings are rejected to
    surface configuration drift before a process starts.
    """

    model_config = SettingsConfigDict(
        env_prefix="LIQUENT_",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    environment: Environment = Environment.LOCAL
    log_level: LogLevel = LogLevel.INFO
    log_format: Literal["text", "json"] = "text"
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8000, ge=1, le=65535)
    artifact_root: Path = Path("./artifacts")
    research_data_root: Path | None = None
    job_concurrency: Literal[1] = 1
    trading_connectivity: Literal["disabled"] = "disabled"
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("LIQUENT_DATABASE_URL", "database_url"),
    )

    @model_validator(mode="after")
    def validate_environment_contract(self) -> "PlatformSettings":
        if self.research_data_root is not None and self.environment not in {
            Environment.LOCAL,
            Environment.CI,
        }:
            raise ValueError(
                "research data root is limited to local and ci until "
                "authentication is implemented"
            )
        if self.environment is Environment.PRODUCTION:
            if self.log_format != "json":
                raise ValueError("production requires LIQUENT_LOG_FORMAT=json")
            if self.http_host != "0.0.0.0":
                raise ValueError("production requires LIQUENT_HTTP_HOST=0.0.0.0")
            if self.database_url is None:
                raise ValueError("production requires the database_url secret file")
            if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
                raise ValueError("production database_url must use postgresql+psycopg")
        return self

    def public_summary(self) -> dict[str, str | int]:
        """Return non-secret startup metadata suitable for logs and diagnostics."""

        return {
            "environment": self.environment.value,
            "log_level": self.log_level.value,
            "log_format": self.log_format,
            "http_host": self.http_host,
            "http_port": self.http_port,
            "job_concurrency": self.job_concurrency,
            "trading_connectivity": self.trading_connectivity,
            "research_start_enabled": str(self.research_data_root is not None).lower(),
        }
