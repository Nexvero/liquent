"""Pure route policy for the future local supervisor Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import (
    CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec,
)


_PREFIX = "/v1.45"
_MAX_TARGET_BYTES = 4096
_MAX_REQUEST_BYTES = 65_536
_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
_CREATION = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
_IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")
_LABELS = frozenset((
    "liquent.supervisor.creation", "liquent.supervisor.handle",
    "liquent.supervisor.control", "liquent.supervisor.launch-document",
    "liquent.supervisor.launch-sha256", "liquent.supervisor.profile",
))


class ManifestHandoffSupervisorEngineApiOperation(str, Enum):
    FIND = "find"
    CREATE = "create"
    INSPECT = "inspect"
    START = "start"
    WAIT = "wait"
    STOP = "stop"
    KILL = "kill"


@dataclass(frozen=True, slots=True)
class AuthorizedManifestHandoffSupervisorEngineApiRoute:
    operation: ManifestHandoffSupervisorEngineApiOperation
    container_id: str | None = None
    creation_id: str | None = None
    request_bytes: int = 0


class ClosedManifestHandoffSupervisorEngineApiRoutePolicy:
    """Classify exact client routes; this does not authorize daemon forwarding."""

    def authorize(
        self, method: str, target: str, body: bytes | None
    ) -> AuthorizedManifestHandoffSupervisorEngineApiRoute:
        try:
            if (
                type(method) is not str
                or method not in {"GET", "POST"}
                or type(target) is not str
                or not target
                or len(target.encode("ascii")) > _MAX_TARGET_BYTES
                or (body is not None and type(body) is not bytes)
                or (body is not None and len(body) > _MAX_REQUEST_BYTES)
            ):
                raise ManifestHandoffRegistryUnavailable
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise ManifestHandoffRegistryUnavailable
            if parsed.path == f"{_PREFIX}/containers/json":
                return self._find(method, parsed.path, parsed.query, body)
            if parsed.path == f"{_PREFIX}/containers/create":
                if method != "POST" or parsed.query or body is None or not body:
                    raise ManifestHandoffRegistryUnavailable
                return AuthorizedManifestHandoffSupervisorEngineApiRoute(
                    ManifestHandoffSupervisorEngineApiOperation.CREATE,
                    request_bytes=len(body),
                )
            return self._container(method, parsed.path, parsed.query, body)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _find(method, path, query, body):
        if method != "GET" or body is not None:
            raise ManifestHandoffRegistryUnavailable
        values = parse_qs(query, keep_blank_values=True, strict_parsing=True)
        if set(values) != {"all", "filters"} or values["all"] != ["1"]:
            raise ManifestHandoffRegistryUnavailable
        filters = json.loads(values["filters"][0], object_pairs_hook=_unique)
        if type(filters) is not dict or set(filters) != {"label"}:
            raise ManifestHandoffRegistryUnavailable
        labels = filters["label"]
        if type(labels) is not list or len(labels) != 1 or type(labels[0]) is not str:
            raise ManifestHandoffRegistryUnavailable
        prefix = "liquent.supervisor.creation="
        if not labels[0].startswith(prefix):
            raise ManifestHandoffRegistryUnavailable
        creation = labels[0][len(prefix):]
        if not _CREATION.fullmatch(creation):
            raise ManifestHandoffRegistryUnavailable
        canonical_filters = json.dumps(
            {"label": [prefix + creation]}, sort_keys=True, separators=(",", ":")
        )
        canonical = urlencode({"all": "1", "filters": canonical_filters})
        if query != canonical:
            raise ManifestHandoffRegistryUnavailable
        return AuthorizedManifestHandoffSupervisorEngineApiRoute(
            ManifestHandoffSupervisorEngineApiOperation.FIND,
            creation_id=creation,
        )

    @staticmethod
    def _container(method, path, query, body):
        prefix = f"{_PREFIX}/containers/"
        if not path.startswith(prefix):
            raise ManifestHandoffRegistryUnavailable
        remainder = path[len(prefix):]
        parts = remainder.split("/")
        if len(parts) != 2 or not _CONTAINER_ID.fullmatch(parts[0]):
            raise ManifestHandoffRegistryUnavailable
        container_id, action = parts
        expected = {
            ("GET", "json", "", None): ManifestHandoffSupervisorEngineApiOperation.INSPECT,
            ("POST", "start", "", b""): ManifestHandoffSupervisorEngineApiOperation.START,
            ("POST", "wait", "condition=not-running", b""): ManifestHandoffSupervisorEngineApiOperation.WAIT,
            ("POST", "stop", "t=10", b""): ManifestHandoffSupervisorEngineApiOperation.STOP,
            ("POST", "kill", "signal=KILL", b""): ManifestHandoffSupervisorEngineApiOperation.KILL,
        }
        operation = expected.get((method, action, query, body))
        if operation is None:
            raise ManifestHandoffRegistryUnavailable
        return AuthorizedManifestHandoffSupervisorEngineApiRoute(
            operation, container_id=container_id,
            request_bytes=0 if body is None else len(body),
        )


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestHandoffRegistryUnavailable
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class AuthorizedManifestHandoffSupervisorCreateRequest:
    profile: str
    image_digest: str
    control_directory: Path
    source_root: Path | None
    target_root: Path


class ClosedManifestHandoffSupervisorCreateRequestPolicy:
    """Validate one canonical create body against fixed host capabilities."""

    __slots__ = (
        "_control", "_recovery", "_source", "_target", "_user", "_writer",
    )

    def __init__(self, *, control_root: Path, source_root: Path,
                 target_root: Path, writer_command: str, recovery_command: str,
                 wrapper_uid: int, wrapper_gid: int) -> None:
        roots = (control_root, source_root, target_root)
        if (
            any(not isinstance(root, Path) or not root.is_absolute()
                or root == Path("/") or ".." in root.parts for root in roots)
            or len(set(roots)) != 3
            or any(type(command) is not str or not command
                   for command in (writer_command, recovery_command))
            or type(wrapper_uid) is not int or wrapper_uid < 1
            or type(wrapper_gid) is not int or wrapper_gid < 1
        ):
            raise ManifestHandoffRegistryUnavailable
        self._control, self._source, self._target = roots
        self._writer, self._recovery = writer_command, recovery_command
        self._user = f"{wrapper_uid}:{wrapper_gid}"

    def authorize(self, body: bytes) -> AuthorizedManifestHandoffSupervisorCreateRequest:
        try:
            if type(body) is not bytes or not body or len(body) > _MAX_REQUEST_BYTES:
                raise ManifestHandoffRegistryUnavailable
            value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique)
            if json.dumps(value, sort_keys=True, separators=(",", ":")).encode() != body:
                raise ManifestHandoffRegistryUnavailable
            if type(value) is not dict or set(value) != {
                "Image", "Entrypoint", "User", "Labels", "HostConfig"
            }:
                raise ManifestHandoffRegistryUnavailable
            image, labels = value["Image"], value["Labels"]
            if (type(image) is not str or not _IMAGE.fullmatch(image)
                    or type(labels) is not dict or set(labels) != _LABELS
                    or any(type(item) is not str or not item for item in labels.values())):
                raise ManifestHandoffRegistryUnavailable
            profile = labels["liquent.supervisor.profile"]
            if profile not in {"writer", "recovery"}:
                raise ManifestHandoffRegistryUnavailable
            entrypoint = value["Entrypoint"]
            expected_command = self._writer if profile == "writer" else self._recovery
            if (type(entrypoint) is not list or len(entrypoint) != 15
                    or entrypoint[0] != expected_command
                    or any(type(item) is not str or not item for item in entrypoint)):
                raise ManifestHandoffRegistryUnavailable
            expectation = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().decode(
                tuple(entrypoint[1:])
            )
            if not all((
                expectation.document_id.value == labels["liquent.supervisor.launch-document"],
                expectation.digest.value == labels["liquent.supervisor.launch-sha256"],
                expectation.creation_id.value == labels["liquent.supervisor.creation"],
                expectation.handle_id.value == labels["liquent.supervisor.handle"],
                expectation.control_directory_id.value == labels["liquent.supervisor.control"],
                expectation.image_digest.value == image,
                expectation.profile.value == profile,
                value["User"] == self._user,
            )):
                raise ManifestHandoffRegistryUnavailable
            source, target, control = self._host_config(value["HostConfig"], profile)
            return AuthorizedManifestHandoffSupervisorCreateRequest(
                profile, image, control, source, target
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _host_config(self, value, profile):
        if type(value) is not dict or set(value) != {
            "AutoRemove", "Binds", "CapDrop", "NetworkMode", "PidMode",
            "Privileged", "ReadonlyRootfs", "RestartPolicy",
        } or not all((
            value["AutoRemove"] is False, value["CapDrop"] == ["ALL"],
            value["NetworkMode"] == "none", value["PidMode"] == "private",
            value["Privileged"] is False, value["ReadonlyRootfs"] is True,
            value["RestartPolicy"] == {"MaximumRetryCount": 0, "Name": "no"},
        )):
            raise ManifestHandoffRegistryUnavailable
        binds = value["Binds"]
        if type(binds) is not list or len(binds) != (4 if profile == "writer" else 3):
            raise ManifestHandoffRegistryUnavailable
        artifacts = self._source_path(binds[0], ":/run/liquent/control:rw")
        launch = self._source_path(
            binds[1], ":/run/liquent/launch/launch-binding.json:ro"
        )
        if artifacts.name != "control-artifacts" or launch.name != "launch-binding.json":
            raise ManifestHandoffRegistryUnavailable
        control = artifacts.parent
        if launch.parent != control or control.parent != self._control:
            raise ManifestHandoffRegistryUnavailable
        if profile == "writer":
            source = self._source_path(binds[2], ":/run/liquent/source:ro")
            target = self._source_path(binds[3], ":/run/liquent/target:rw")
            self._within(source, self._source)
        else:
            source = None
            target = self._source_path(binds[2], ":/run/liquent/target:ro")
        self._within(target, self._target)
        return source, target, control

    @staticmethod
    def _source_path(binding, suffix):
        if type(binding) is not str or not binding.endswith(suffix):
            raise ManifestHandoffRegistryUnavailable
        value = binding[:-len(suffix)]
        path = Path(value)
        if not value or not path.is_absolute() or ".." in path.parts or ":" in value:
            raise ManifestHandoffRegistryUnavailable
        return path

    @staticmethod
    def _within(value: Path, root: Path) -> None:
        if value != root and root not in value.parents:
            raise ManifestHandoffRegistryUnavailable
