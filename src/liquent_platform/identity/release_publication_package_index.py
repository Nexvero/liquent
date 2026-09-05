"""Strict package-index mapping above one injected provider transport."""

from __future__ import annotations

from liquent_platform.identity.ports import PackageIndexProviderTransport
from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationExecutionId,
    ReleasePublicationTarget,
    ReleasePublicationTargetObservation,
    VerifiedReleasePublicationArtifacts,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexArtifactRecord,
    PackageIndexCreateRecord,
    PackageIndexProviderConfiguration,
    ReleasePublicationProviderUnavailable,
)


class PackageIndexReleasePublicationAdapter:
    """Inspect and create only one preconfigured immutable package target."""

    __slots__ = ("_configuration", "_transport")

    def __init__(
        self,
        configuration: PackageIndexProviderConfiguration,
        transport: PackageIndexProviderTransport,
    ) -> None:
        if type(configuration) is not PackageIndexProviderConfiguration:
            raise ReleasePublicationProviderUnavailable
        self._configuration = configuration
        self._transport = transport

    def __repr__(self) -> str:
        return "PackageIndexReleasePublicationAdapter()"

    def inspect_target(self, target):
        try:
            self._require_target(target)
            record = self._transport.inspect_package(self._configuration, target)
            if record is None:
                return None
            if type(record) is not PackageIndexArtifactRecord:
                raise ReleasePublicationProviderUnavailable
            return ReleasePublicationTargetObservation(
                record.canonical_artifact_id,
                record.provider_revision,
                record.package_name,
                record.package_version,
                record.wheel_sha256,
                record.visible,
            )
        except ReleasePublicationProviderUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationProviderUnavailable

    def create_immutable(self, target, artifacts, idempotency_key):
        try:
            self._require_target(target)
            if type(artifacts) is not VerifiedReleasePublicationArtifacts:
                raise ReleasePublicationProviderUnavailable
            if artifacts.package_version != target.package_version:
                raise ReleasePublicationProviderUnavailable
            if type(idempotency_key) not in {
                ReleasePublicationExecutionId,
                ReleasePublicationAttemptId,
            }:
                raise ReleasePublicationProviderUnavailable
            record = self._transport.create_package(
                self._configuration, target, artifacts, idempotency_key.value
            )
            if type(record) is not PackageIndexCreateRecord:
                raise ReleasePublicationProviderUnavailable
            return ReleasePublicationCreateAcknowledgement(record.provider_request_id)
        except ReleasePublicationProviderUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationProviderUnavailable

    def _require_target(self, target: object) -> None:
        if (
            type(target) is not ReleasePublicationTarget
            or target.provider_kind != "package-index"
            or target.target_name != self._configuration.target_name
            or target.package_name != "liquent"
        ):
            raise ReleasePublicationProviderUnavailable
