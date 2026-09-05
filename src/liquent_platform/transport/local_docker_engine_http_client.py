"""Bounded Unix-socket Docker HTTP client for the closed supervisor engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import http.client
import json
import os
from pathlib import Path
import socket
import stat
from typing import Protocol
from urllib.parse import urlencode

from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import (
    CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec,
)


_API_PREFIX = "/v1.45"
_MAX_RESPONSE_BYTES = 1_048_576
_MAX_FIND_RESULTS = 2
_LABEL_KEYS = frozenset((
    "liquent.supervisor.creation",
    "liquent.supervisor.handle",
    "liquent.supervisor.control",
    "liquent.supervisor.launch-document",
    "liquent.supervisor.launch-sha256",
    "liquent.supervisor.profile",
))


class _DockerHttpTransport(Protocol):
    def request(
        self, method: str, path: str, body: bytes | None, *, maximum: int
    ) -> tuple[int, bytes]: ...

    def close(self) -> None: ...


class _UnixSocketHttpConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: Path, *, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._socket_path = str(socket_path)

    def connect(self) -> None:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self.timeout)
        try:
            connection.connect(self._socket_path)
        except Exception:
            connection.close()
            raise
        self.sock = connection


class _UnixSocketDockerHttpTransport:
    __slots__ = ("_closed", "_socket_path", "_timeout")

    def __init__(self, socket_path: Path, *, timeout: float) -> None:
        self._socket_path = socket_path
        self._timeout = timeout
        self._closed = False

    def request(
        self, method: str, path: str, body: bytes | None, *, maximum: int
    ) -> tuple[int, bytes]:
        if self._closed:
            raise ManifestHandoffRegistryUnavailable
        connection = _UnixSocketHttpConnection(
            self._socket_path, timeout=self._timeout
        )
        response = None
        try:
            headers = {"Accept": "application/json", "Connection": "close"}
            if body is not None:
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(body))
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            declared = response.getheader("Content-Length")
            if declared is not None and int(declared) > maximum:
                raise ManifestHandoffRegistryUnavailable
            payload = response.read(maximum + 1)
            if len(payload) > maximum:
                raise ManifestHandoffRegistryUnavailable
            return response.status, payload
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if response is not None:
                response.close()
            connection.close()

    def close(self) -> None:
        self._closed = True


class LocalDockerEngineHttpClient:
    """Translate a fixed subset of one local Docker Engine API."""

    __slots__ = (
        "_closed", "_control_directory_resolver", "_profile_commands",
        "_identity", "_stop_seconds", "_transport", "_user",
    )

    def __init__(
        self,
        socket_path: Path,
        *,
        control_directory_resolver: Callable[
            [ManifestHandoffSupervisorControlDirectoryId], Path | None
        ],
        writer_command: tuple[str, ...],
        recovery_command: tuple[str, ...],
        user: str | None = None,
        identity_policy: ManifestHandoffSupervisorLaunchIdentityPolicy | None = None,
        timeout_seconds: float = 30.0,
        stop_seconds: int = 10,
        transport_factory: Callable[[Path, float], _DockerHttpTransport] | None = None,
    ) -> None:
        if (
            not isinstance(socket_path, Path)
            or not socket_path.is_absolute()
            or not callable(control_directory_resolver)
            or not self._command(writer_command)
            or not self._command(recovery_command)
            or (identity_policy is None and (type(user) is not str or not user))
            or (identity_policy is not None and (
                type(identity_policy) is not ManifestHandoffSupervisorLaunchIdentityPolicy
                or user is not None
            ))
            or type(timeout_seconds) not in (int, float)
            or timeout_seconds <= 0
            or type(stop_seconds) is not int
            or stop_seconds <= 0
            or (transport_factory is not None and not callable(transport_factory))
        ):
            raise ManifestHandoffRegistryUnavailable
        try:
            factory = transport_factory or (
                lambda path, timeout: _UnixSocketDockerHttpTransport(
                    path, timeout=timeout
                )
            )
            self._transport = factory(socket_path, float(timeout_seconds))
            if self._transport is None:
                raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        self._closed = False
        self._control_directory_resolver = control_directory_resolver
        self._profile_commands = {
            "writer": writer_command,
            "recovery": recovery_command,
        }
        self._stop_seconds = stop_seconds
        self._identity = identity_policy
        self._user = user if identity_policy is None else identity_policy.docker_user

    def __repr__(self) -> str:
        return "LocalDockerEngineHttpClient()"

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._transport.close()
            except Exception:
                raise ManifestHandoffRegistryUnavailable from None

    def find(self, labels: Mapping[str, str]) -> list[Mapping[str, object]]:
        self._require_open()
        if type(labels) is not dict or set(labels) != {"liquent.supervisor.creation"}:
            raise ManifestHandoffRegistryUnavailable
        filters = json.dumps(
            {"label": [f"liquent.supervisor.creation={labels['liquent.supervisor.creation']}"]},
            sort_keys=True, separators=(",", ":"),
        )
        path = f"{_API_PREFIX}/containers/json?{urlencode({'all': '1', 'filters': filters})}"
        raw = self._json("GET", path, None, statuses=(200,))
        if type(raw) is not list or len(raw) > _MAX_FIND_RESULTS:
            raise ManifestHandoffRegistryUnavailable
        found = []
        for item in raw:
            if type(item) is not dict or type(item.get("Id")) is not str:
                raise ManifestHandoffRegistryUnavailable
            inspected = self.inspect(item["Id"])
            if inspected is None:
                raise ManifestHandoffRegistryUnavailable
            found.append(inspected)
        return found

    def create(self, specification: Mapping[str, object]) -> Mapping[str, object]:
        self._require_open()
        normalized = self._create_specification(specification)
        raw = self._json(
            "POST", f"{_API_PREFIX}/containers/create",
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode(),
            statuses=(201,),
        )
        if type(raw) is not dict or set(raw) - {"Id", "Warnings"} or type(raw.get("Id")) is not str:
            raise ManifestHandoffRegistryUnavailable
        inspected = self.inspect(raw["Id"])
        if inspected is None:
            raise ManifestHandoffRegistryUnavailable
        return inspected

    def inspect(self, container_id: str) -> Mapping[str, object] | None:
        self._require_id(container_id)
        status, body = self._request(
            "GET", f"{_API_PREFIX}/containers/{container_id}/json", None
        )
        if status == 404:
            if body not in (b"", b"{}"):
                self._decode(body)
            return None
        if status != 200:
            raise ManifestHandoffRegistryUnavailable
        return self._observation(self._decode(body))

    def start(self, container_id: str) -> None:
        self._empty("POST", f"{_API_PREFIX}/containers/{self._id(container_id)}/start", (204,))

    def wait(self, container_id: str) -> Mapping[str, object]:
        value = self._json(
            "POST",
            f"{_API_PREFIX}/containers/{self._id(container_id)}/wait?condition=not-running",
            b"", statuses=(200,),
        )
        if type(value) is not dict or type(value.get("StatusCode")) is not int:
            raise ManifestHandoffRegistryUnavailable
        observed = self.inspect(container_id)
        if observed is None:
            raise ManifestHandoffRegistryUnavailable
        return observed

    def stop(self, container_id: str) -> None:
        self._empty(
            "POST",
            f"{_API_PREFIX}/containers/{self._id(container_id)}/stop?t={self._stop_seconds}",
            (204, 304),
        )

    def kill(self, container_id: str) -> None:
        self._empty(
            "POST", f"{_API_PREFIX}/containers/{self._id(container_id)}/kill?signal=KILL",
            (204, 304),
        )

    def _create_specification(self, value: Mapping[str, object]) -> dict[str, object]:
        expected = {
            "image", "labels", "profile", "network_mode", "restart_policy",
            "auto_remove", "readonly_rootfs", "cap_drop", "privileged", "pid_mode",
            "source_root", "target_root",
        }
        if type(value) is not dict or set(value) != expected:
            raise ManifestHandoffRegistryUnavailable
        labels = value["labels"]
        profile = value["profile"]
        if (
            type(labels) is not dict or set(labels) != _LABEL_KEYS
            or profile not in self._profile_commands
            or labels.get("liquent.supervisor.profile") != profile
            or any(type(item) is not str or not item for item in labels.values())
            or value["network_mode"] != "none"
            or value["restart_policy"] != "no"
            or value["auto_remove"] is not False
            or value["readonly_rootfs"] is not True
            or value["cap_drop"] != ("ALL",)
            or value["privileged"] is not False
            or value["pid_mode"] != "private"
            or type(value["image"]) is not str
        ):
            raise ManifestHandoffRegistryUnavailable
        try:
            directory_id = ManifestHandoffSupervisorControlDirectoryId(
                labels["liquent.supervisor.control"]
            )
            binds = self._mounts(
                directory_id, value["source_root"], value["target_root"], profile
            )
            entrypoint = self._entrypoint(labels, value["image"], profile)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        return {
            "Image": value["image"],
            "Entrypoint": list(entrypoint),
            "User": self._user,
            "Labels": dict(labels),
            "HostConfig": {
                "AutoRemove": False, "Binds": list(binds),
                "CapDrop": ["ALL"], "NetworkMode": "none", "PidMode": "private",
                "Privileged": False, "ReadonlyRootfs": True,
                "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            },
        }

    def _observation(self, raw: object) -> Mapping[str, object]:
        try:
            config = raw["Config"]
            host = raw["HostConfig"]
            labels = config["Labels"]
            state = raw["State"]["Status"]
            if type(raw) is not dict or type(labels) is not dict or set(labels) != _LABEL_KEYS:
                raise ValueError
            directory_id = ManifestHandoffSupervisorControlDirectoryId(
                labels["liquent.supervisor.control"]
            )
            source_root, target_root = self._observed_mounts(
                directory_id, labels["liquent.supervisor.profile"], host["Binds"]
            )
            if (config["Entrypoint"] != list(self._entrypoint(
                        labels, config["Image"], labels["liquent.supervisor.profile"]
                    ))):
                raise ValueError
            return {
                "id": raw["Id"], "image": config["Image"], "labels": dict(labels),
                "state": state, "network_mode": host["NetworkMode"],
                "restart_policy": host["RestartPolicy"]["Name"],
                "auto_remove": host["AutoRemove"],
                "readonly_rootfs": host["ReadonlyRootfs"],
                "cap_drop": tuple(host["CapDrop"]), "privileged": host["Privileged"],
                "pid_mode": host["PidMode"], "source_root": source_root,
                "target_root": target_root,
            }
        except (KeyError, TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def _mounts(self, directory_id, source_root, target_root, profile):
        base = self._control_directory_resolver(directory_id)
        if not isinstance(base, Path) or not base.is_absolute():
            raise ManifestHandoffRegistryUnavailable
        artifacts = base / "control-artifacts"
        launch = base / "launch-binding.json"
        try:
            base_facts = os.lstat(base)
            artifact_facts = os.lstat(artifacts)
            launch_facts = os.lstat(launch)
            if (not stat.S_ISDIR(base_facts.st_mode)
                    or not stat.S_ISDIR(artifact_facts.st_mode)
                    or not stat.S_ISREG(launch_facts.st_mode)
                    or launch_facts.st_nlink != 1
                    or launch_facts.st_size < 1 or launch_facts.st_size > 65_536
                    or ":" in str(base) or "\n" in str(base)):
                raise ManifestHandoffRegistryUnavailable
            expected_mode = 0o600 if self._identity is None else 0o640
            if stat.S_IMODE(launch_facts.st_mode) != expected_mode:
                raise ManifestHandoffRegistryUnavailable
            if self._identity is not None and (
                    launch_facts.st_uid != self._identity.host_owner_uid
                    or launch_facts.st_gid != self._identity.reader_gid):
                raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        control = (
            f"{artifacts}:/run/liquent/control:rw",
            f"{launch}:/run/liquent/launch/launch-binding.json:ro",
        )
        self._require_data_root(target_root)
        if profile == "recovery":
            return control + (f"{target_root}:/run/liquent/target:ro",)
        self._require_data_root(source_root)
        return control + (
            f"{source_root}:/run/liquent/source:ro",
            f"{target_root}:/run/liquent/target:rw",
        )

    def _observed_mounts(self, directory_id, profile, binds):
        if type(binds) is not list:
            raise ManifestHandoffRegistryUnavailable
        base = self._control_directory_resolver(directory_id)
        if not isinstance(base, Path) or not base.is_absolute():
            raise ManifestHandoffRegistryUnavailable
        control = [
            f"{base / 'control-artifacts'}:/run/liquent/control:rw",
            f"{base / 'launch-binding.json'}:/run/liquent/launch/launch-binding.json:ro",
        ]
        try:
            if profile == "writer" and len(binds) == 4 and binds[:2] == control:
                source = Path(binds[2].removesuffix(":/run/liquent/source:ro"))
                target = Path(binds[3].removesuffix(":/run/liquent/target:rw"))
                if (binds[2] != f"{source}:/run/liquent/source:ro"
                        or binds[3] != f"{target}:/run/liquent/target:rw"):
                    raise ValueError
                self._require_data_root(source)
                self._require_data_root(target)
                return source, target
            if profile == "recovery" and len(binds) == 3 and binds[:2] == control:
                target = Path(binds[2].removesuffix(":/run/liquent/target:ro"))
                if binds[2] != f"{target}:/run/liquent/target:ro":
                    raise ValueError
                self._require_data_root(target)
                return None, target
            raise ValueError
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _require_data_root(value):
        try:
            if not isinstance(value, Path) or not value.is_absolute():
                raise ManifestHandoffRegistryUnavailable
            facts = os.lstat(value)
            if (not stat.S_ISDIR(facts.st_mode) or stat.S_ISLNK(facts.st_mode)
                    or ":" in str(value) or "\n" in str(value)
                    or "\r" in str(value)):
                raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _entrypoint(self, labels, image, profile):
        try:
            expectation = ManifestHandoffSupervisorLaunchDocumentExpectation(
                ManifestHandoffSupervisorControlArtifactId(
                    labels["liquent.supervisor.launch-document"]),
                ManifestHandoffSupervisorLaunchDocumentDigest(
                    labels["liquent.supervisor.launch-sha256"]),
                ManifestHandoffSupervisorCreationId(
                    labels["liquent.supervisor.creation"]),
                ManifestHandoffSupervisorHandleId(
                    labels["liquent.supervisor.handle"]),
                ManifestHandoffSupervisorControlDirectoryId(
                    labels["liquent.supervisor.control"]),
                ManifestHandoffSupervisorImageDigest(image),
                ManifestHandoffSupervisorEngineProfile(profile),
            )
            arguments = CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().encode(
                expectation
            )
            return self._profile_commands[profile] + arguments
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _json(self, method: str, path: str, body: bytes | None, *, statuses: tuple[int, ...]):
        status, payload = self._request(method, path, body)
        if status not in statuses:
            raise ManifestHandoffRegistryUnavailable
        return self._decode(payload)

    def _empty(self, method: str, path: str, statuses: tuple[int, ...]) -> None:
        status, payload = self._request(method, path, b"")
        if status not in statuses or payload not in (b"", b"{}"):
            raise ManifestHandoffRegistryUnavailable

    def _request(self, method: str, path: str, body: bytes | None) -> tuple[int, bytes]:
        self._require_open()
        try:
            return self._transport.request(method, path, body, maximum=_MAX_RESPONSE_BYTES)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _decode(payload: bytes):
        try:
            return json.loads(payload, object_pairs_hook=_unique_pairs)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _require_open(self) -> None:
        if self._closed:
            raise ManifestHandoffRegistryUnavailable

    def _require_id(self, value: str) -> None:
        self._require_open()
        self._id(value)

    @staticmethod
    def _id(value: str) -> str:
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ManifestHandoffRegistryUnavailable
        return value

    @staticmethod
    def _command(value: object) -> bool:
        return type(value) is tuple and bool(value) and all(type(item) is str and item for item in value)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError
        value[key] = item
    return value
