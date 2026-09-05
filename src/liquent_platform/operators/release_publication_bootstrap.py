"""Owner-only one-time bootstrap for the release-publication control plane."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_publication import (
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexProviderConfiguration,
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
    ReleasePublicationBootstrapConflict,
    ReleasePublicationBootstrapUnavailable,
)
from liquent_platform.persistence.release_publication_bootstrap import (
    DatabaseInitialReleasePublicationControlPlaneBootstrap,
)


class ReleasePublicationBootstrapOperatorInputRejected(Exception):
    code = "release_publication_bootstrap_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationBootstrapOperatorUnavailable(Exception):
    code = "release_publication_bootstrap_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


_TARGET = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?")


@dataclass(frozen=True, slots=True)
class ReleasePublicationBootstrapRequest:
    bootstrap_id: ReleasePublicationBootstrapId = field(repr=False)
    channel: ReleasePublicationChannelDefinition = field(repr=False)


def _input(action):
    try:
        return action()
    except ReleasePublicationOperatorInputRejected:
        raise ReleasePublicationBootstrapOperatorInputRejected from None
    except ReleasePublicationOperatorUnavailable:
        raise ReleasePublicationBootstrapOperatorUnavailable from None


def load_request(path: Path) -> ReleasePublicationBootstrapRequest:
    value = _input(lambda: _json_file(path, {
        "bootstrap_id", "package_name", "provider_kind", "target_name",
    }))
    try:
        bootstrap_id = ReleasePublicationBootstrapId(
            _string(value["bootstrap_id"])
        )
        package_name = _string(value["package_name"])
        provider_kind = _string(value["provider_kind"])
        target_name = _string(value["target_name"])
        if (
            package_name != "liquent"
            or provider_kind != "package-index"
            or not _TARGET.fullmatch(target_name)
        ):
            raise ReleasePublicationBootstrapOperatorInputRejected
        PackageIndexProviderConfiguration(
            "https://bootstrap-validation.invalid", target_name, "validation"
        )
        return ReleasePublicationBootstrapRequest(
            bootstrap_id,
            ReleasePublicationChannelDefinition(
                package_name, provider_kind, target_name
            ),
        )
    except ReleasePublicationBootstrapOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePublicationBootstrapOperatorInputRejected from None


def run_operator(*, database_url_file: Path, request_file: Path):
    request = load_request(request_file)
    database_url = _input(lambda: _private_text(database_url_file, 8192))
    if database_url.endswith("\n"):
        database_url = database_url[:-1]
    try:
        database_url = _string(database_url)
    except Exception:
        raise ReleasePublicationBootstrapOperatorInputRejected from None
    engine = None
    try:
        engine = build_engine(database_url)
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleasePublicationBootstrapOperatorUnavailable
        material = SecureIdentityAuthorityMaterialGenerator()
        return DatabaseInitialReleasePublicationControlPlaneBootstrap(
            engine,
            generate_publisher_authority_id=(
                material.new_release_publisher_authority_id
            ),
            generate_channel_id=material.new_release_publication_channel_id,
            generate_channel_revision_id=(
                material.new_release_publication_channel_policy_revision_id
            ),
        ).bootstrap(request.bootstrap_id, request.channel)
    except ReleasePublicationBootstrapOperatorUnavailable:
        raise
    except ReleasePublicationBootstrapConflict:
        raise
    except ReleasePublicationBootstrapUnavailable:
        raise ReleasePublicationBootstrapOperatorUnavailable from None
    except Exception:
        raise ReleasePublicationBootstrapOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-publication-bootstrap")
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
    except ReleasePublicationBootstrapOperatorInputRejected:
        _fail(ReleasePublicationBootstrapOperatorInputRejected.code, 2)
    except ReleasePublicationBootstrapConflict:
        _fail("release_publication_bootstrap_operator_conflict", 3)
    except Exception:
        _fail(ReleasePublicationBootstrapOperatorUnavailable.code, 4)
    if result is None:
        sys.stdout.write('{"outcome":"not_bootstrapped"}\n')
        return 5
    sys.stdout.write(json.dumps({
        "bootstrap_id": result.bootstrap_id.value,
        "channel_id": result.channel_id.value,
        "channel_revision_id": result.channel_revision_id.value,
        "outcome": "bootstrapped",
        "publisher_authority_id": result.publisher_authority_id.value,
    }, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
