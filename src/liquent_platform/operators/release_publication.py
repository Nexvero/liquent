"""Owner-only offline operator for one release-publication work unit."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationArtifactBytes,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResult,
    ReleasePublicationWorkResultKind,
    ReleasePublisherAuthorityId,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexHttpPolicy,
    PackageIndexProviderConfiguration,
)
from liquent_platform.operators.release_publication_worker_composition import (
    compose_release_publication_worker,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
    ReleasePublicationArtifactFiles,
)
from liquent_platform.transport.package_index_composition import (
    compose_package_index_publication,
)


class ReleasePublicationOperatorInputRejected(Exception):
    code = "release_publication_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationOperatorUnavailable(Exception):
    code = "release_publication_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleasePublicationArtifactSourceConfiguration:
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    bundle_path: Path = field(repr=False)
    signature_path: Path = field(repr=False)
    promotion_evidence_path: Path = field(repr=False)


@dataclass(frozen=True, slots=True)
class ReleasePublicationProviderConfigurationFile:
    origin: str = field(repr=False)
    target_name: str = field(repr=False)
    credential_path: Path = field(repr=False)
    policy: PackageIndexHttpPolicy = field(repr=False)


class SingleHandoffReleasePublicationArtifactSource:
    """Bind three configured paths only to one system-of-record binding."""

    __slots__ = ("_configuration",)

    def __init__(
        self, configuration: ReleasePublicationArtifactSourceConfiguration
    ) -> None:
        self._configuration = configuration

    def __repr__(self) -> str:
        return "SingleHandoffReleasePublicationArtifactSource()"

    def load_artifacts(
        self, binding: ReleasePublicationArtifactBinding
    ) -> ReleasePublicationArtifactBytes:
        if (
            type(binding) is not ReleasePublicationArtifactBinding
            or binding.handoff_id != self._configuration.handoff_id
        ):
            raise ReleasePublicationOperatorUnavailable
        files = ReleasePublicationArtifactFiles(
            self._configuration.bundle_path,
            self._configuration.signature_path,
            self._configuration.promotion_evidence_path,
        )
        try:
            return BoundLocalReleasePublicationArtifactSource(
                {binding: files}
            ).load_artifacts(binding)
        except Exception:
            raise ReleasePublicationOperatorUnavailable from None


def _private_bytes(path: Path, maximum: int) -> bytes:
    descriptor: int | None = None
    try:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ReleasePublicationOperatorInputRejected
        no_follow = getattr(os, "O_NOFOLLOW", None)
        close_on_exec = getattr(os, "O_CLOEXEC", None)
        if no_follow is None or close_on_exec is None:
            raise ReleasePublicationOperatorUnavailable
        descriptor = os.open(path, os.O_RDONLY | no_follow | close_on_exec)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
            or metadata.st_size > maximum
        ):
            raise ReleasePublicationOperatorUnavailable
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(8192, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise ReleasePublicationOperatorUnavailable
        value = b"".join(chunks)
        if not value:
            raise ReleasePublicationOperatorInputRejected
        return value
    except (ReleasePublicationOperatorInputRejected, ReleasePublicationOperatorUnavailable):
        raise
    except Exception:
        raise ReleasePublicationOperatorUnavailable from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _private_text(path: Path, maximum: int = 65536) -> str:
    try:
        return _private_bytes(path, maximum).decode("utf-8")
    except (ReleasePublicationOperatorInputRejected, ReleasePublicationOperatorUnavailable):
        raise
    except UnicodeError:
        raise ReleasePublicationOperatorInputRejected from None


def _members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleasePublicationOperatorInputRejected
        result[key] = value
    return result


def _json_file(path: Path, keys: set[str]) -> dict[str, Any]:
    raw = _private_text(path)
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_members,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ReleasePublicationOperatorInputRejected()
            ),
        )
    except ReleasePublicationOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationOperatorInputRejected from None
    if not isinstance(value, dict) or set(value) != keys:
        raise ReleasePublicationOperatorInputRejected
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if raw != canonical:
        raise ReleasePublicationOperatorInputRejected
    return value


def _string(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ReleasePublicationOperatorInputRejected
    return value


def _absolute(value: object) -> Path:
    path = Path(_string(value))
    if not path.is_absolute():
        raise ReleasePublicationOperatorInputRejected
    return path


def _identifier(path: Path, constructor):
    value = _private_text(path, 4097)
    if value.endswith("\n"):
        value = value[:-1]
    try:
        return constructor(_string(value))
    except ReleasePublicationOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationOperatorInputRejected from None


def load_work_request(path: Path) -> ReleasePublicationWorkRequest:
    value = _json_file(path, {
        "execution_id", "handoff_id", "publisher_authority_id", "channel_id",
        "expected_channel_revision",
    })
    try:
        return ReleasePublicationWorkRequest(
            ReleasePublicationExecutionId(_string(value["execution_id"])),
            ReleasePublicationHandoffId(_string(value["handoff_id"])),
            ReleasePublisherAuthorityId(_string(value["publisher_authority_id"])),
            ReleasePublicationChannelId(_string(value["channel_id"])),
            ReleasePublicationChannelPolicyRevisionId(
                _string(value["expected_channel_revision"])
            ),
        )
    except ReleasePublicationOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationOperatorInputRejected from None


def load_artifact_source(
    path: Path,
) -> ReleasePublicationArtifactSourceConfiguration:
    value = _json_file(path, {
        "handoff_id", "bundle_path", "signature_path", "promotion_evidence_path",
    })
    try:
        result = ReleasePublicationArtifactSourceConfiguration(
            ReleasePublicationHandoffId(_string(value["handoff_id"])),
            _absolute(value["bundle_path"]),
            _absolute(value["signature_path"]),
            _absolute(value["promotion_evidence_path"]),
        )
    except ReleasePublicationOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationOperatorInputRejected from None
    if result.signature_path.name != result.bundle_path.name + ".sshsig":
        raise ReleasePublicationOperatorInputRejected
    return result


def _positive_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ReleasePublicationOperatorInputRejected
    return float(value)


def _positive_integer(value: object) -> int:
    if type(value) is not int or value < 1:
        raise ReleasePublicationOperatorInputRejected
    return value


def load_provider_configuration(
    path: Path,
) -> ReleasePublicationProviderConfigurationFile:
    value = _json_file(path, {
        "origin", "target_name", "credential_path", "connect_timeout_seconds",
        "read_timeout_seconds", "total_timeout_seconds", "request_max_bytes",
        "response_max_bytes",
    })
    try:
        policy = PackageIndexHttpPolicy(
            timedelta(seconds=_positive_number(value["connect_timeout_seconds"])),
            timedelta(seconds=_positive_number(value["read_timeout_seconds"])),
            timedelta(seconds=_positive_number(value["total_timeout_seconds"])),
            _positive_integer(value["response_max_bytes"]),
            _positive_integer(value["request_max_bytes"]),
        )
        origin = _string(value["origin"])
        target_name = _string(value["target_name"])
        PackageIndexProviderConfiguration(origin, target_name, "validation")
        return ReleasePublicationProviderConfigurationFile(
            origin,
            target_name,
            _absolute(value["credential_path"]),
            policy,
        )
    except ReleasePublicationOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationOperatorInputRejected from None


def _new(identifier):
    try:
        return identifier(secrets.token_urlsafe(32))
    except Exception:
        raise ReleasePublicationOperatorUnavailable from None


def run_operator(
    *,
    database_url_file: Path,
    request_file: Path,
    artifact_source_file: Path,
    provider_file: Path,
    executor_id_file: Path,
    promotion_verifier_id_file: Path,
) -> ReleasePublicationWorkResult:
    request = load_work_request(request_file)
    artifact_configuration = load_artifact_source(artifact_source_file)
    if artifact_configuration.handoff_id != request.handoff_id:
        raise ReleasePublicationOperatorInputRejected
    provider_configuration = load_provider_configuration(provider_file)
    executor_id = _identifier(executor_id_file, ReleasePublicationExecutorId)
    verifier_id = _identifier(
        promotion_verifier_id_file, ReleasePromotionVerifierId
    )
    database_url = _private_text(database_url_file, 8192)
    if database_url.endswith("\n"):
        database_url = database_url[:-1]
    database_url = _string(database_url)
    engine = None
    provider = None
    try:
        engine = build_engine(database_url)
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleasePublicationOperatorUnavailable
        provider = compose_package_index_publication(
            origin=provider_configuration.origin,
            target_name=provider_configuration.target_name,
            credential_path=provider_configuration.credential_path,
            policy=provider_configuration.policy,
        )
        composition = compose_release_publication_worker(
            engine=engine,
            provider=provider,
            artifact_source=SingleHandoffReleasePublicationArtifactSource(
                artifact_configuration
            ),
            executor_id=executor_id,
            promotion_verifier_id=verifier_id,
            generate_attempt_id=lambda: _new(ReleasePublicationAttemptId),
            generate_receipt_id=lambda: _new(
                ReleasePublicationProviderReceiptId
            ),
            generate_recovery_id=lambda: _new(ReleasePublicationRecoveryId),
            generate_reassessment_id=lambda: _new(
                ReleasePublicationReassessmentId
            ),
        )
        engine = None
        provider = None
        with composition:
            result = composition.worker.process(request)
        if type(result) is not ReleasePublicationWorkResult:
            raise ReleasePublicationOperatorUnavailable
        return result
    except ReleasePublicationOperatorUnavailable:
        raise
    except Exception:
        raise ReleasePublicationOperatorUnavailable from None
    finally:
        if provider is not None:
            try:
                provider.close()
            except Exception:
                pass
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-publication")
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--artifact-source", required=True, type=Path)
    parser.add_argument("--provider", required=True, type=Path)
    parser.add_argument("--executor-id-file", required=True, type=Path)
    parser.add_argument("--promotion-verifier-id-file", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


_OUTCOMES = {
    ReleasePublicationWorkResultKind.PUBLISHED: ("published", 0),
    ReleasePublicationWorkResultKind.PUBLISHED_REASSESSMENT_REQUIRED: (
        "published_reassessment_required", 6
    ),
    ReleasePublicationWorkResultKind.NOT_PUBLISHED: ("not_published", 7),
    ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT: (
        "publication_conflict", 8
    ),
    ReleasePublicationWorkResultKind.PENDING_RECONCILIATION: (
        "pending_reconciliation", 9
    ),
    ReleasePublicationWorkResultKind.NOT_ACTIONABLE: ("not_actionable", 5),
}


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_operator(
            database_url_file=arguments.database_url_file,
            request_file=arguments.request,
            artifact_source_file=arguments.artifact_source,
            provider_file=arguments.provider,
            executor_id_file=arguments.executor_id_file,
            promotion_verifier_id_file=arguments.promotion_verifier_id_file,
        )
        outcome = _OUTCOMES.get(result.kind)
        if outcome is None:
            raise ReleasePublicationOperatorUnavailable
    except ReleasePublicationOperatorInputRejected:
        _fail(ReleasePublicationOperatorInputRejected.code, 2)
    except Exception:
        _fail(ReleasePublicationOperatorUnavailable.code, 4)
    name, status = outcome
    sys.stdout.write(json.dumps({"outcome": name}, separators=(",", ":")) + "\n")
    return status
