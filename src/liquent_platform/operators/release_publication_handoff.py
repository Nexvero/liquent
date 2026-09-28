"""Owner-only operator for an authorized release-publication handoff."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.operators.release_publication import (
    ReleasePublicationOperatorInputRejected,
    ReleasePublicationOperatorUnavailable,
    _json_file,
    _private_bytes,
    _private_text,
    _string,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationHandoffConflict,
    ReleasePublicationHandoffUnavailable,
)
from liquent_platform.persistence.release_publication_handoff import (
    DatabaseAuthorizedReleasePublicationHandoff,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)


_VERIFIER_ID = ReleasePromotionVerifierId(
    "liquent-release-publication-handoff-v1"
)


class ReleasePublicationHandoffOperatorInputRejected(Exception):
    code = "release_publication_handoff_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationHandoffOperatorUnavailable(Exception):
    code = "release_publication_handoff_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleasePublicationHandoffRequest:
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    decision_id: ReleasePublicationDecisionId = field(repr=False)
    publisher_authority_id: ReleasePublisherAuthorityId = field(repr=False)
    channel_id: ReleasePublicationChannelId = field(repr=False)
    channel_revision_id: ReleasePublicationChannelPolicyRevisionId = field(repr=False)
    bundle_path: Path = field(repr=False)
    signature_path: Path = field(repr=False)
    promotion_evidence_path: Path = field(repr=False)
    execution_id: ReleasePublicationExecutionId = field(repr=False)


def _input(action):
    try:
        return action()
    except ReleasePublicationOperatorInputRejected:
        raise ReleasePublicationHandoffOperatorInputRejected from None
    except ReleasePublicationOperatorUnavailable:
        raise ReleasePublicationHandoffOperatorUnavailable from None


def _path(value: object) -> Path:
    path = Path(_string(value))
    if not path.is_absolute():
        raise ReleasePublicationHandoffOperatorInputRejected
    return path


def load_request(path: Path) -> ReleasePublicationHandoffRequest:
    value = _input(lambda: _json_file(path, {
        "bundle_path", "channel_id", "channel_revision_id", "decision_id",
        "execution_id", "handoff_id", "promotion_evidence_path",
        "publisher_authority_id", "signature_path",
    }))
    try:
        request = ReleasePublicationHandoffRequest(
            ReleasePublicationHandoffId(_string(value["handoff_id"])),
            ReleasePublicationDecisionId(_string(value["decision_id"])),
            ReleasePublisherAuthorityId(
                _string(value["publisher_authority_id"])
            ),
            ReleasePublicationChannelId(_string(value["channel_id"])),
            ReleasePublicationChannelPolicyRevisionId(
                _string(value["channel_revision_id"])
            ),
            _path(value["bundle_path"]),
            _path(value["signature_path"]),
            _path(value["promotion_evidence_path"]),
            ReleasePublicationExecutionId(_string(value["execution_id"])),
        )
    except ReleasePublicationHandoffOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationHandoffOperatorInputRejected from None
    if request.signature_path.name != request.bundle_path.name + ".sshsig":
        raise ReleasePublicationHandoffOperatorInputRejected
    return request


def run_operator(*, database_url_file: Path, request_file: Path):
    request = load_request(request_file)
    database_url = _input(lambda: _private_text(database_url_file, 8192))
    if database_url.endswith("\n"):
        database_url = database_url[:-1]
    try:
        database_url = _string(database_url)
    except Exception:
        raise ReleasePublicationHandoffOperatorInputRejected from None
    for path, maximum in (
        (request.bundle_path, 64 * 1024 * 1024),
        (request.signature_path, 65536),
        (request.promotion_evidence_path, 65536),
    ):
        _input(lambda path=path, maximum=maximum: _private_bytes(path, maximum))
    engine = None
    try:
        engine = build_engine(database_url)
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleasePublicationHandoffOperatorUnavailable
        projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
            engine, verification_identity=_VERIFIER_ID
        )
        result = DatabaseAuthorizedReleasePublicationHandoff(
            engine, registry_projection=projection
        ).accept_handoff(
            request.handoff_id,
            request.decision_id,
            request.publisher_authority_id,
            request.channel_id,
            request.channel_revision_id,
            str(request.bundle_path),
            str(request.signature_path),
            str(request.promotion_evidence_path),
        )
        return request, result
    except ReleasePublicationHandoffOperatorUnavailable:
        raise
    except ReleasePublicationHandoffConflict:
        raise
    except ReleasePublicationHandoffUnavailable:
        raise ReleasePublicationHandoffOperatorUnavailable from None
    except Exception:
        raise ReleasePublicationHandoffOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-publication-handoff")
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        request, result = run_operator(
            database_url_file=arguments.database_url_file,
            request_file=arguments.request,
        )
    except ReleasePublicationHandoffOperatorInputRejected:
        _fail(ReleasePublicationHandoffOperatorInputRejected.code, 2)
    except ReleasePublicationHandoffConflict:
        _fail("release_publication_handoff_operator_conflict", 3)
    except Exception:
        _fail(ReleasePublicationHandoffOperatorUnavailable.code, 4)
    if result is None:
        sys.stdout.write('{"outcome":"not_accepted"}\n')
        return 5
    sys.stdout.write(json.dumps({
        "channel_id": result.channel_id.value,
        "channel_revision_id": result.channel_revision_id.value,
        "decision_id": result.decision_id.value,
        "execution_id": request.execution_id.value,
        "handoff_id": result.handoff_id.value,
        "outcome": "accepted",
    }, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
