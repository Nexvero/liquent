"""Owner-only operator for persistent publication-executor registration."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_publication import (
    ReleasePublicationExecutorRegistrationId,
)
from liquent_platform.operators.release_publication import (
    ReleasePublicationOperatorInputRejected,
    ReleasePublicationOperatorUnavailable,
    _json_file,
    _private_text,
    _string,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationExecutorRegistrationUnavailable,
)
from liquent_platform.persistence.release_publication_executor_registration import (
    DatabaseReleasePublicationExecutorRegistration,
)


class ReleasePublicationExecutorOperatorInputRejected(Exception):
    code = "release_publication_executor_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationExecutorOperatorUnavailable(Exception):
    code = "release_publication_executor_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleasePublicationExecutorRegistrationRequest:
    registration_id: ReleasePublicationExecutorRegistrationId = field(repr=False)


def _input(action):
    try:
        return action()
    except ReleasePublicationOperatorInputRejected:
        raise ReleasePublicationExecutorOperatorInputRejected from None
    except ReleasePublicationOperatorUnavailable:
        raise ReleasePublicationExecutorOperatorUnavailable from None


def load_request(path: Path) -> ReleasePublicationExecutorRegistrationRequest:
    value = _input(lambda: _json_file(path, {"registration_id"}))
    try:
        return ReleasePublicationExecutorRegistrationRequest(
            ReleasePublicationExecutorRegistrationId(
                _string(value["registration_id"])
            )
        )
    except Exception:
        raise ReleasePublicationExecutorOperatorInputRejected from None


def run_operator(*, database_url_file: Path, request_file: Path):
    request = load_request(request_file)
    database_url = _input(lambda: _private_text(database_url_file, 8192))
    if database_url.endswith("\n"):
        database_url = database_url[:-1]
    try:
        database_url = _string(database_url)
    except Exception:
        raise ReleasePublicationExecutorOperatorInputRejected from None
    engine = None
    try:
        engine = build_engine(database_url)
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleasePublicationExecutorOperatorUnavailable
        material = SecureIdentityAuthorityMaterialGenerator()
        return DatabaseReleasePublicationExecutorRegistration(
            engine,
            generate_executor_id=material.new_release_publication_executor_id,
        ).register(request.registration_id)
    except ReleasePublicationExecutorOperatorUnavailable:
        raise
    except ReleasePublicationExecutorRegistrationUnavailable:
        raise ReleasePublicationExecutorOperatorUnavailable from None
    except Exception:
        raise ReleasePublicationExecutorOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-publication-executor")
    parser.add_argument("command", choices=("register",))
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_operator(
            database_url_file=arguments.database_url_file,
            request_file=arguments.request,
        )
    except ReleasePublicationExecutorOperatorInputRejected:
        _fail(ReleasePublicationExecutorOperatorInputRejected.code, 2)
    except Exception:
        _fail(ReleasePublicationExecutorOperatorUnavailable.code, 4)
    sys.stdout.write(json.dumps({
        "executor_id": result.executor_id.value,
        "outcome": "registered",
        "registration_id": result.registration_id.value,
    }, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
