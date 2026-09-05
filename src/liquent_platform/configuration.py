"""Fail-fast runtime configuration for Liquent process roles."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
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
    oidc_login_origin: str | None = None
    oidc_login_lifetime_seconds: int | None = Field(default=None, ge=1)
    oidc_session_lifetime_seconds: int | None = Field(default=None, ge=1)
    oidc_callback_rejection: str | None = None
    oidc_callback_unavailable: str | None = None
    oidc_connect_timeout_seconds: int | None = Field(default=None, ge=1)
    oidc_read_timeout_seconds: int | None = Field(default=None, ge=1)
    oidc_total_timeout_seconds: int | None = Field(default=None, ge=1)
    oidc_token_response_max_bytes: int | None = Field(default=None, ge=1)
    oidc_jwks_response_max_bytes: int | None = Field(default=None, ge=1)
    oidc_jwks_cache_ttl_seconds: int | None = Field(default=None, ge=1)
    manifest_handoff_supervisor_mode: Literal["candidate"] | None = None
    manifest_handoff_supervisor_backend_instance_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    manifest_handoff_supervisor_docker_socket: Path | None = None
    manifest_handoff_supervisor_control_root: Path | None = None
    manifest_handoff_supervisor_host_owner_uid: int | None = Field(
        default=None, ge=1, le=2_147_483_647
    )
    manifest_handoff_supervisor_reader_gid: int | None = Field(
        default=None, ge=1, le=2_147_483_647
    )
    manifest_handoff_supervisor_wrapper_uid: int | None = Field(
        default=None, ge=1, le=2_147_483_647
    )
    manifest_handoff_supervisor_wrapper_gid: int | None = Field(
        default=None, ge=1, le=2_147_483_647
    )

    @field_validator("job_concurrency", mode="before")
    @classmethod
    def parse_single_job_concurrency(cls, value: object) -> object:
        return 1 if value == "1" else value

    @model_validator(mode="after")
    def validate_environment_contract(self) -> "PlatformSettings":
        oidc_values = self._oidc_values()
        if any(value is not None for value in oidc_values) and not all(
            value is not None for value in oidc_values
        ):
            raise ValueError("oidc runtime settings must be provided together")
        if self.oidc_enabled:
            assert self.oidc_connect_timeout_seconds is not None
            assert self.oidc_read_timeout_seconds is not None
            assert self.oidc_total_timeout_seconds is not None
            if self.oidc_connect_timeout_seconds > self.oidc_total_timeout_seconds:
                raise ValueError("oidc connect timeout must not exceed total timeout")
            if self.oidc_read_timeout_seconds > self.oidc_total_timeout_seconds:
                raise ValueError("oidc read timeout must not exceed total timeout")
        supervisor_values = self._manifest_handoff_supervisor_values()
        if any(value is not None for value in supervisor_values) and not all(
            value is not None for value in supervisor_values
        ):
            raise ValueError(
                "manifest handoff supervisor settings must be provided together"
            )
        if self.manifest_handoff_supervisor_enabled:
            socket_path = self.manifest_handoff_supervisor_docker_socket
            control_root = self.manifest_handoff_supervisor_control_root
            assert socket_path is not None and control_root is not None
            if not self._closed_absolute_path(socket_path) or socket_path == Path("/"):
                raise ValueError(
                    "manifest handoff supervisor docker socket must be an absolute closed path"
                )
            if not self._closed_absolute_path(control_root) or control_root == Path("/"):
                raise ValueError(
                    "manifest handoff supervisor control root must be an absolute closed path"
                )
            if socket_path == control_root:
                raise ValueError(
                    "manifest handoff supervisor socket and control root must differ"
                )
            if self.database_url is None:
                raise ValueError(
                    "manifest handoff supervisor requires the database_url secret file"
                )
            if (
                self.manifest_handoff_supervisor_wrapper_gid
                != self.manifest_handoff_supervisor_reader_gid
                or self.manifest_handoff_supervisor_wrapper_uid
                == self.manifest_handoff_supervisor_host_owner_uid
            ):
                raise ValueError(
                    "manifest handoff supervisor identity policy is invalid"
                )
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

    def _oidc_values(self) -> tuple[object | None, ...]:
        return (
            self.oidc_login_origin,
            self.oidc_login_lifetime_seconds,
            self.oidc_session_lifetime_seconds,
            self.oidc_callback_rejection,
            self.oidc_callback_unavailable,
            self.oidc_connect_timeout_seconds,
            self.oidc_read_timeout_seconds,
            self.oidc_total_timeout_seconds,
            self.oidc_token_response_max_bytes,
            self.oidc_jwks_response_max_bytes,
            self.oidc_jwks_cache_ttl_seconds,
        )

    def _manifest_handoff_supervisor_values(self) -> tuple[object | None, ...]:
        return (
            self.manifest_handoff_supervisor_mode,
            self.manifest_handoff_supervisor_backend_instance_id,
            self.manifest_handoff_supervisor_docker_socket,
            self.manifest_handoff_supervisor_control_root,
            self.manifest_handoff_supervisor_host_owner_uid,
            self.manifest_handoff_supervisor_reader_gid,
            self.manifest_handoff_supervisor_wrapper_uid,
            self.manifest_handoff_supervisor_wrapper_gid,
        )

    @staticmethod
    def _closed_absolute_path(value: Path) -> bool:
        return value.is_absolute() and ".." not in value.parts

    @property
    def oidc_enabled(self) -> bool:
        return all(value is not None for value in self._oidc_values())

    @property
    def manifest_handoff_supervisor_enabled(self) -> bool:
        return all(
            value is not None
            for value in self._manifest_handoff_supervisor_values()
        )

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
            "oidc_enabled": str(self.oidc_enabled).lower(),
            "manifest_handoff_supervisor_enabled": str(
                self.manifest_handoff_supervisor_enabled
            ).lower(),
        }
