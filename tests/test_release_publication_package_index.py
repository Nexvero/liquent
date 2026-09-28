from dataclasses import FrozenInstanceError

import pytest

from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBytes,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublicationTarget,
    VerifiedReleasePublicationArtifacts,
)
from liquent_platform.identity.release_publication_package_index import (
    PackageIndexReleasePublicationAdapter,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexArtifactRecord,
    PackageIndexCreateRecord,
    PackageIndexProviderConfiguration,
    ReleasePublicationProviderUnavailable,
)


CONFIGURATION = PackageIndexProviderConfiguration(
    "https://packages.example.test", "stable", "secret-publication-token"
)
TARGET = ReleasePublicationTarget(
    ReleasePublicationChannelId("channel-267"),
    ReleasePublicationChannelPolicyRevisionId("revision-267"),
    "package-index", "stable", "liquent", "1.2.3",
)
EXECUTION = ReleasePublicationExecutionId("execution-267")
ATTEMPT = ReleasePublicationAttemptId("attempt-267")
ARTIFACTS = VerifiedReleasePublicationArtifacts(
    EXECUTION, ATTEMPT, ReleasePublicationHandoffId("handoff-267"), "1.2.3",
    "a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64,
    ReleasePublicationArtifactBytes("bundle.tar.gz", b"bundle", b"signature", b"evidence"),
)


class Transport:
    def __init__(self, inspection=None, created=None, error=None):
        self.inspection = inspection
        self.created = created or PackageIndexCreateRecord("request-267")
        self.error = error
        self.inspect_calls = []
        self.create_calls = []

    def inspect_package(self, configuration, target):
        self.inspect_calls.append((configuration, target))
        if self.error:
            raise self.error
        return self.inspection

    def create_package(self, configuration, target, artifacts, idempotency_key):
        self.create_calls.append(
            (configuration, target, artifacts, idempotency_key)
        )
        if self.error:
            raise self.error
        return self.created


@pytest.mark.parametrize("origin", [
    "http://packages.example.test",
    "https://user@packages.example.test",
    "https://packages.example.test/path",
    "https://packages.example.test?query=1",
    "https://packages.example.test#fragment",
    "https://PACKAGES.example.test",
    " https://packages.example.test",
    "https://packages.example.test/",
])
def test_configuration_accepts_only_one_canonical_https_origin(origin):
    with pytest.raises(ValueError):
        PackageIndexProviderConfiguration(origin, "stable", "credential")


def test_configuration_is_frozen_and_keeps_sensitive_values_out_of_repr():
    assert repr(CONFIGURATION) == "PackageIndexProviderConfiguration()"
    with pytest.raises(FrozenInstanceError):
        CONFIGURATION.credential = "replacement"  # type: ignore[misc]
    with pytest.raises(ValueError):
        PackageIndexProviderConfiguration(
            "https://packages.example.test", "stable", "secret\nheader"
        )
    with pytest.raises(ValueError):
        PackageIndexProviderConfiguration(
            "https://packages.example.test", "stable", "two tokens"
        )


def test_confirmed_absence_is_the_only_none_inspection_result():
    transport = Transport()
    adapter = PackageIndexReleasePublicationAdapter(CONFIGURATION, transport)
    assert adapter.inspect_target(TARGET) is None
    assert transport.inspect_calls == [(CONFIGURATION, TARGET)]


def test_canonical_record_maps_exactly_to_observation():
    record = PackageIndexArtifactRecord(
        "artifact-267", "provider-revision-267", "liquent", "1.2.3",
        "b" * 64, True,
    )
    result = PackageIndexReleasePublicationAdapter(
        CONFIGURATION, Transport(inspection=record)
    ).inspect_target(TARGET)
    assert result.canonical_artifact_id == "artifact-267"
    assert result.provider_revision == "provider-revision-267"
    assert result.wheel_sha256 == "b" * 64
    assert result.visible is True


@pytest.mark.parametrize("target", [
    ReleasePublicationTarget(
        TARGET.channel_id, TARGET.channel_revision_id,
        "other-provider", "stable", "liquent", "1.2.3",
    ),
    ReleasePublicationTarget(
        TARGET.channel_id, TARGET.channel_revision_id,
        "package-index", "other", "liquent", "1.2.3",
    ),
    ReleasePublicationTarget(
        TARGET.channel_id, TARGET.channel_revision_id,
        "package-index", "stable", "other", "1.2.3",
    ),
])
def test_unbound_target_is_rejected_before_transport(target):
    transport = Transport()
    adapter = PackageIndexReleasePublicationAdapter(CONFIGURATION, transport)
    with pytest.raises(ReleasePublicationProviderUnavailable):
        adapter.inspect_target(target)
    assert transport.inspect_calls == []


@pytest.mark.parametrize("idempotency_key", [EXECUTION, ATTEMPT])
def test_create_passes_exact_stable_idempotency_identity(idempotency_key):
    transport = Transport()
    result = PackageIndexReleasePublicationAdapter(
        CONFIGURATION, transport
    ).create_immutable(TARGET, ARTIFACTS, idempotency_key)
    assert result.provider_request_id == "request-267"
    assert len(transport.create_calls) == 1
    assert transport.create_calls[0][3] == idempotency_key.value


def test_mismatched_payload_is_rejected_before_transport():
    transport = Transport()
    different = VerifiedReleasePublicationArtifacts(
        EXECUTION, ATTEMPT, ARTIFACTS.handoff_id, "9.9.9",
        ARTIFACTS.bundle_sha256, ARTIFACTS.wheel_sha256,
        ARTIFACTS.checksums_sha256, ARTIFACTS.signature_sha256,
        ARTIFACTS.promotion_evidence_sha256, ARTIFACTS.artifacts,
    )
    with pytest.raises(ReleasePublicationProviderUnavailable):
        PackageIndexReleasePublicationAdapter(
            CONFIGURATION, transport
        ).create_immutable(TARGET, different, ATTEMPT)
    assert transport.create_calls == []


@pytest.mark.parametrize("operation", ["inspect", "create"])
def test_transport_failure_is_detail_free_and_never_retried(operation):
    transport = Transport(error=TimeoutError("secret provider detail"))
    adapter = PackageIndexReleasePublicationAdapter(CONFIGURATION, transport)
    with pytest.raises(ReleasePublicationProviderUnavailable) as raised:
        if operation == "inspect":
            adapter.inspect_target(TARGET)
        else:
            adapter.create_immutable(TARGET, ARTIFACTS, ATTEMPT)
    assert raised.value.args == ("release_publication_provider_unavailable",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert len(transport.inspect_calls) + len(transport.create_calls) == 1


def test_untyped_transport_results_are_technical_unavailability():
    with pytest.raises(ReleasePublicationProviderUnavailable):
        PackageIndexReleasePublicationAdapter(
            CONFIGURATION, Transport(inspection="provider body")
        ).inspect_target(TARGET)
    with pytest.raises(ReleasePublicationProviderUnavailable):
        PackageIndexReleasePublicationAdapter(
            CONFIGURATION, Transport(created="provider body")
        ).create_immutable(TARGET, ARTIFACTS, ATTEMPT)
