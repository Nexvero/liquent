"""Fail-closed adapter for one constructively configured local Docker engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    AcceptedManifestHandoffSupervisorTermination,
    CreateManifestHandoffSupervisorContainer,
    CreatedManifestHandoffSupervisorContainer,
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
    ObservedManifestHandoffSupervisorContainer,
    StartManifestHandoffSupervisorContainer,
    StartedManifestHandoffSupervisorContainer,
    TerminateManifestHandoffSupervisorContainer,
    WaitManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeContainerId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CREATION = "liquent.supervisor.creation"
_HANDLE = "liquent.supervisor.handle"
_CONTROL = "liquent.supervisor.control"
_PROFILE = "liquent.supervisor.profile"
_LAUNCH_DOCUMENT = "liquent.supervisor.launch-document"
_LAUNCH_DIGEST = "liquent.supervisor.launch-sha256"


class _LocalDockerEngineClient(Protocol):
    def find(self, labels: Mapping[str, str]) -> list[Mapping[str, object]]: ...
    def create(self, specification: Mapping[str, object]) -> Mapping[str, object]: ...
    def inspect(self, container_id: str) -> Mapping[str, object] | None: ...
    def start(self, container_id: str) -> None: ...
    def wait(self, container_id: str) -> Mapping[str, object]: ...
    def stop(self, container_id: str) -> None: ...
    def kill(self, container_id: str) -> None: ...


class LocalDockerManifestHandoffSupervisorEngine:
    """Enforce closed profiles over a client already bound to one local daemon."""

    __slots__ = ("_client", "_images")

    def __init__(self, client: _LocalDockerEngineClient, *,
                 writer_image: ManifestHandoffSupervisorImageDigest,
                 recovery_image: ManifestHandoffSupervisorImageDigest) -> None:
        if not all((
            type(writer_image) is ManifestHandoffSupervisorImageDigest,
            type(recovery_image) is ManifestHandoffSupervisorImageDigest,
        )):
            raise ManifestHandoffRegistryUnavailable
        self._client = client
        self._images = {
            ManifestHandoffSupervisorEngineProfile.WRITER: writer_image,
            ManifestHandoffSupervisorEngineProfile.RECOVERY: recovery_image,
        }

    def __repr__(self) -> str:
        return "LocalDockerManifestHandoffSupervisorEngine()"

    def create(self, request):
        if type(request) is not CreateManifestHandoffSupervisorContainer:
            raise ManifestHandoffRegistryUnavailable
        if request.image_digest != self._images[request.profile]:
            return ManifestHandoffSupervisorEngineConflict()
        labels = self._labels(request)
        try:
            found = self._client.find({_CREATION: request.creation_id.value})
            if len(found) > 1:
                return ManifestHandoffSupervisorEngineConflict()
            if found:
                return self._created(request, found[0])
            raw = self._client.create(self._specification(request, labels))
            return self._created(request, raw)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def inspect(self, request):
        if type(request) is not InspectManifestHandoffSupervisorContainer:
            raise ManifestHandoffRegistryUnavailable
        return self._observe(request.runtime_container_id)

    def start(self, request):
        if type(request) is not StartManifestHandoffSupervisorContainer:
            raise ManifestHandoffRegistryUnavailable
        try:
            raw = self._client.inspect(request.runtime_container_id.value)
            if raw is None:
                raise ManifestHandoffRegistryUnavailable
            observation = self._observation(request.runtime_container_id, raw)
            if observation.state is not ManifestHandoffSupervisorEngineState.CREATED:
                return ManifestHandoffSupervisorEngineConflict()
            self._client.start(request.runtime_container_id.value)
            return StartedManifestHandoffSupervisorContainer(request.runtime_container_id)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def wait_terminal(self, request):
        if type(request) is not WaitManifestHandoffSupervisorContainer:
            raise ManifestHandoffRegistryUnavailable
        try:
            raw = self._client.wait(request.runtime_container_id.value)
            observation = self._observation(request.runtime_container_id, raw)
            if observation.state not in (
                ManifestHandoffSupervisorEngineState.EXITED,
                ManifestHandoffSupervisorEngineState.DEAD,
            ):
                raise ManifestHandoffRegistryUnavailable
            return observation
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def terminate(self, request):
        if type(request) is not TerminateManifestHandoffSupervisorContainer:
            raise ManifestHandoffRegistryUnavailable
        try:
            raw = self._client.inspect(request.runtime_container_id.value)
            if raw is None:
                raise ManifestHandoffRegistryUnavailable
            observation = self._observation(request.runtime_container_id, raw)
            if observation.state in (
                ManifestHandoffSupervisorEngineState.EXITED,
                ManifestHandoffSupervisorEngineState.DEAD,
            ):
                return AcceptedManifestHandoffSupervisorTermination(
                    request.runtime_container_id, request.terminate_id)
            try:
                self._client.stop(request.runtime_container_id.value)
            except Exception:
                self._client.kill(request.runtime_container_id.value)
            return AcceptedManifestHandoffSupervisorTermination(
                request.runtime_container_id, request.terminate_id)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _observe(self, container_id):
        try:
            raw = self._client.inspect(container_id.value)
            if raw is None:
                raise ManifestHandoffRegistryUnavailable
            return self._observation(container_id, raw)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _labels(request):
        return {_CREATION: request.creation_id.value, _HANDLE: request.handle_id.value,
                _CONTROL: request.control_directory_id.value,
                _LAUNCH_DOCUMENT: request.launch_document_id.value,
                _LAUNCH_DIGEST: request.launch_document_digest.value,
                _PROFILE: request.profile.value}

    @staticmethod
    def _specification(request, labels):
        return {"image": request.image_digest.value, "labels": labels,
                "profile": request.profile.value, "network_mode": "none",
                "restart_policy": "no", "auto_remove": False,
                "readonly_rootfs": True, "cap_drop": ("ALL",),
                "privileged": False, "pid_mode": "private",
                "source_root": request.binding.source_root,
                "target_root": request.binding.target_root}

    def _created(self, request, raw):
        observation = self._observation_from_raw(raw)
        if not self._matches(request, raw, observation):
            return ManifestHandoffSupervisorEngineConflict()
        return CreatedManifestHandoffSupervisorContainer(
            request.handle_id, request.creation_id, observation.runtime_container_id,
            request.control_directory_id, request.image_digest,
            request.launch_document_id, request.launch_document_digest,
            request.profile, request.binding)

    def _observation(self, expected_id, raw):
        observation = self._observation_from_raw(raw)
        if (observation.runtime_container_id != expected_id
                or observation.image_digest != self._images[observation.profile]
                or not self._secure(raw)):
            raise ManifestHandoffRegistryUnavailable
        return observation

    @staticmethod
    def _observation_from_raw(raw):
        try:
            labels = raw["labels"]
            return ObservedManifestHandoffSupervisorContainer(
                ManifestHandoffSupervisorRuntimeContainerId(raw["id"]),
                ManifestHandoffSupervisorCreationId(labels[_CREATION]),
                ManifestHandoffSupervisorImageDigest(raw["image"]),
                ManifestHandoffSupervisorControlArtifactId(labels[_LAUNCH_DOCUMENT]),
                ManifestHandoffSupervisorLaunchDocumentDigest(labels[_LAUNCH_DIGEST]),
                ManifestHandoffSupervisorEngineProfile(labels[_PROFILE]),
                ManifestHandoffSupervisorEngineState(raw["state"]),
                raw.get("source_root"), raw["target_root"],
            )
        except (KeyError, TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def _matches(self, request, raw, observation):
        return (observation.creation_id == request.creation_id
                and observation.image_digest == request.image_digest
                and observation.launch_document_id == request.launch_document_id
                and observation.launch_document_digest == request.launch_document_digest
                and observation.profile is request.profile
                and observation.source_root == (
                    request.binding.source_root
                    if request.profile is ManifestHandoffSupervisorEngineProfile.WRITER
                    else None)
                and observation.target_root == request.binding.target_root
                and raw.get("labels") == self._labels(request)
                and self._secure(raw))

    @staticmethod
    def _secure(raw):
        return all((raw.get("network_mode") == "none",
                    raw.get("restart_policy") == "no",
                    raw.get("auto_remove") is False,
                    raw.get("readonly_rootfs") is True,
                    raw.get("cap_drop") == ("ALL",),
                    raw.get("privileged") is False,
                    raw.get("pid_mode") == "private"))
