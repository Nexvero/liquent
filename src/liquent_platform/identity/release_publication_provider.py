"""Controlled local configuration and records for one package-index provider."""

from dataclasses import dataclass, field
from datetime import timedelta
from urllib.parse import urlsplit


class ReleasePublicationProviderUnavailable(Exception):
    code = "release_publication_provider_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class PackageIndexHttpPolicy:
    connect_timeout: timedelta
    read_timeout: timedelta
    total_timeout: timedelta
    response_max_bytes: int
    request_max_bytes: int

    def __post_init__(self) -> None:
        for value, name in (
            (self.connect_timeout, "connect timeout"),
            (self.read_timeout, "read timeout"),
            (self.total_timeout, "total timeout"),
        ):
            if not isinstance(value, timedelta) or value <= timedelta(0):
                raise ValueError(f"package index {name} must be positive")
        if self.connect_timeout > self.total_timeout or self.read_timeout > self.total_timeout:
            raise ValueError("package index phase timeout exceeds total timeout")
        for value, name in (
            (self.response_max_bytes, "response byte limit"),
            (self.request_max_bytes, "request byte limit"),
        ):
            if type(value) is not int or value < 1:
                raise ValueError(f"package index {name} must be positive")


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"package index {name} must be a non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"package index {name} contains a control character")
    return value


@dataclass(frozen=True, slots=True)
class PackageIndexProviderConfiguration:
    """One exact HTTPS origin, target, and short-lived credential."""

    origin: str = field(repr=False)
    target_name: str = field(repr=False)
    credential: str = field(repr=False)

    def __post_init__(self) -> None:
        origin = _text(self.origin, "origin")
        _text(self.target_name, "target name")
        credential = _text(self.credential, "credential")
        if any(character.isspace() for character in credential):
            raise ValueError("package index credential contains whitespace")
        try:
            parsed = urlsplit(origin)
            port = parsed.port
        except ValueError:
            raise ValueError("package index origin is invalid") from None
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or origin != f"https://{parsed.hostname}{f':{port}' if port else ''}"
        ):
            raise ValueError("package index origin must be one canonical HTTPS origin")
        if len(credential.encode("utf-8")) > 4096:
            raise ValueError("package index credential is too large")


@dataclass(frozen=True, slots=True)
class PackageIndexArtifactRecord:
    """Canonical immutable metadata returned by the provider transport."""

    canonical_artifact_id: str = field(repr=False)
    provider_revision: str = field(repr=False)
    package_name: str
    package_version: str
    wheel_sha256: str = field(repr=False)
    visible: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.canonical_artifact_id, "artifact id"),
            (self.provider_revision, "provider revision"),
            (self.package_name, "package name"),
            (self.package_version, "package version"),
            (self.wheel_sha256, "wheel sha256"),
        ):
            _text(value, name)
        if type(self.visible) is not bool:
            raise ValueError("package index visibility must be boolean")


@dataclass(frozen=True, slots=True)
class PackageIndexCreateRecord:
    """Minimal acknowledgement returned by one create-only transport call."""

    provider_request_id: str = field(repr=False)

    def __post_init__(self) -> None:
        _text(self.provider_request_id, "provider request id")
