"""Owner-only challenge and apply process for release-key activation."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_authority import (
    ReleaseActivationReviewerId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSigningKeyId,
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
    ReleaseKeyActivationConflict,
    ReleaseKeyActivationUnavailable,
)
from liquent_platform.persistence.release_key_activation import (
    DatabaseReleaseKeyActivation,
    DatabaseReleaseKeyActivationChallenge,
)
from liquent_platform.transport.release_key_activation_verification import (
    ReleaseActivationReviewerTrust,
    ReleaseKeyActivationVerificationUnavailable,
    compose_release_key_activation_verification,
)


REVIEWER_TRUST_PATH = Path("/etc/liquent/release-activation-reviewers.json")


class ReleaseKeyActivationOperatorInputRejected(Exception):
    code = "release_key_activation_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseKeyActivationOperatorUnavailable(Exception):
    code = "release_key_activation_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleaseKeyActivationRequest:
    actor_authority_id: ReleaseRegistryLifecycleAuthorityId = field(repr=False)
    change_id: ReleaseRegistryLifecycleChangeId = field(repr=False)
    expected_revision: ReleaseRegistrySetRevisionId = field(repr=False)
    key_id: ReleaseSigningKeyId = field(repr=False)


def _input(action):
    try:
        return action()
    except ReleasePublicationOperatorInputRejected:
        raise ReleaseKeyActivationOperatorInputRejected from None
    except ReleasePublicationOperatorUnavailable:
        raise ReleaseKeyActivationOperatorUnavailable from None


def load_request(path: Path) -> ReleaseKeyActivationRequest:
    value = _input(lambda: _json_file(path, {
        "actor_authority_id", "change_id", "expected_revision", "key_id",
    }))
    try:
        return ReleaseKeyActivationRequest(
            ReleaseRegistryLifecycleAuthorityId(
                _string(value["actor_authority_id"])
            ),
            ReleaseRegistryLifecycleChangeId(_string(value["change_id"])),
            ReleaseRegistrySetRevisionId(_string(value["expected_revision"])),
            ReleaseSigningKeyId(_string(value["key_id"])),
        )
    except Exception:
        raise ReleaseKeyActivationOperatorInputRejected from None


def load_reviewer_trust(path: Path = REVIEWER_TRUST_PATH):
    value = _input(lambda: _json_file(path, {"reviewers"}))
    reviewers = value["reviewers"]
    if type(reviewers) is not list or not reviewers:
        raise ReleaseKeyActivationOperatorInputRejected
    result = []
    try:
        for reviewer in reviewers:
            if type(reviewer) is not dict or set(reviewer) != {
                "reviewer_id", "public_key", "fingerprint",
            }:
                raise ReleaseKeyActivationOperatorInputRejected
            result.append(ReleaseActivationReviewerTrust(
                ReleaseActivationReviewerId(_string(reviewer["reviewer_id"])),
                _string(reviewer["public_key"]),
                _string(reviewer["fingerprint"]),
            ))
        return tuple(result)
    except ReleaseKeyActivationOperatorInputRejected:
        raise
    except Exception:
        raise ReleaseKeyActivationOperatorInputRejected from None


def _database(path: Path) -> str:
    value = _input(lambda: _private_text(path, 8192))
    if value.endswith("\n"):
        value = value[:-1]
    try:
        return _string(value)
    except Exception:
        raise ReleaseKeyActivationOperatorInputRejected from None


def _materialize(path: Path, value: bytes) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ReleaseKeyActivationOperatorInputRejected
    try:
        parent = path.parent.stat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.geteuid()
            or stat.S_IMODE(parent.st_mode) & 0o077
            or path.exists()
            or path.is_symlink()
        ):
            raise ReleaseKeyActivationOperatorUnavailable
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        try:
            written = 0
            while written < len(value):
                count = os.write(descriptor, value[written:])
                if count < 1:
                    raise ReleaseKeyActivationOperatorUnavailable
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except (ReleaseKeyActivationOperatorInputRejected, ReleaseKeyActivationOperatorUnavailable):
        raise
    except Exception:
        raise ReleaseKeyActivationOperatorUnavailable from None
    finally:
        if "temporary" in locals():
            try:
                temporary.unlink()
            except OSError:
                pass


def run_challenge(
    *, database_url_file: Path, request_file: Path, output: Path,
) -> bytes | None:
    request = load_request(request_file)
    engine = None
    try:
        engine = build_engine(_database(database_url_file))
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleaseKeyActivationOperatorUnavailable
        challenge = DatabaseReleaseKeyActivationChallenge(engine).get_challenge(
            request.change_id,
            request.actor_authority_id,
            request.key_id,
            request.expected_revision,
        )
        if challenge is not None:
            _materialize(output, challenge)
        return challenge
    except ReleaseKeyActivationOperatorInputRejected:
        raise
    except ReleaseKeyActivationOperatorUnavailable:
        raise
    except ReleaseKeyActivationUnavailable:
        raise ReleaseKeyActivationOperatorUnavailable from None
    except Exception:
        raise ReleaseKeyActivationOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def run_apply(
    *,
    database_url_file: Path,
    request_file: Path,
    proof_file: Path,
    approval_file: Path,
    reviewer_trust_path: Path = REVIEWER_TRUST_PATH,
):
    request = load_request(request_file)
    proof = _input(lambda: _private_bytes(proof_file, 16_384))
    approval = _input(lambda: _private_bytes(approval_file, 16_384))
    reviewers = load_reviewer_trust(reviewer_trust_path)
    try:
        verification = compose_release_key_activation_verification(
            reviewers=reviewers
        )
    except Exception:
        raise ReleaseKeyActivationOperatorUnavailable from None
    engine = None
    try:
        engine = build_engine(_database(database_url_file))
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleaseKeyActivationOperatorUnavailable
        material = SecureIdentityAuthorityMaterialGenerator()
        return DatabaseReleaseKeyActivation(
            engine,
            proof_verifier=verification.proof_verifier,
            approval_verifier=verification.approval_verifier,
            generate_revision_id=material.new_release_registry_set_revision_id,
        ).activate_key(
            request.change_id,
            request.actor_authority_id,
            request.key_id,
            request.expected_revision,
            proof,
            approval,
        )
    except (ReleaseKeyActivationOperatorInputRejected, ReleaseKeyActivationOperatorUnavailable):
        raise
    except ReleaseKeyActivationConflict:
        raise
    except (ReleaseKeyActivationUnavailable, ReleaseKeyActivationVerificationUnavailable):
        raise ReleaseKeyActivationOperatorUnavailable from None
    except Exception:
        raise ReleaseKeyActivationOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-key-activation")
    modes = parser.add_subparsers(dest="mode", required=True)
    challenge = modes.add_parser("challenge")
    challenge.add_argument("--database-url-file", required=True, type=Path)
    challenge.add_argument("--request", required=True, type=Path)
    challenge.add_argument("--output", required=True, type=Path)
    apply = modes.add_parser("apply")
    apply.add_argument("--database-url-file", required=True, type=Path)
    apply.add_argument("--request", required=True, type=Path)
    apply.add_argument("--proof", required=True, type=Path)
    apply.add_argument("--approval", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.mode == "challenge":
            result = run_challenge(
                database_url_file=arguments.database_url_file,
                request_file=arguments.request,
                output=arguments.output,
            )
            if result is None:
                sys.stdout.write('{"outcome":"not_challenged"}\n')
                return 5
            sys.stdout.write('{"outcome":"challenge_materialized"}\n')
            return 0
        result = run_apply(
            database_url_file=arguments.database_url_file,
            request_file=arguments.request,
            proof_file=arguments.proof,
            approval_file=arguments.approval,
        )
    except ReleaseKeyActivationOperatorInputRejected:
        _fail(ReleaseKeyActivationOperatorInputRejected.code, 2)
    except ReleaseKeyActivationConflict:
        _fail("release_key_activation_operator_conflict", 3)
    except Exception:
        _fail(ReleaseKeyActivationOperatorUnavailable.code, 4)
    if result is None:
        sys.stdout.write('{"outcome":"not_activated"}\n')
        return 5
    sys.stdout.write(json.dumps({
        "change_id": result.change_id.value,
        "key_id": result.key_id.value,
        "outcome": "activated",
        "registry_revision_id": result.revision_id.value,
        "reviewer_id": result.reviewer_id.value,
    }, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
