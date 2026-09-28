"""Owner-only offline operator for persistent release promotion evidence."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.ports import CurrentReleaseAuthorityRegistryProjection
from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.operators.initial_bootstrap import _read_private
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from tools.release_promotion_verifier import (
    PromotionRejected,
    PromotionUnavailable,
    verify_release_promotion_with_projection,
)


class ReleasePromotionOperatorInputRejected(Exception):
    code = "release_promotion_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePromotionOperatorUnavailable(Exception):
    code = "release_promotion_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleasePromotionRequest:
    bundle_path: Path = field(repr=False)
    signature_path: Path = field(repr=False)
    key_id: str = field(repr=False)
    evidence_path: Path = field(repr=False)


@dataclass(frozen=True, slots=True)
class MaterializedPromotionEvidence:
    evidence_path: Path = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise ReleasePromotionOperatorInputRejected
    return value


def load_request(path: Path) -> ReleasePromotionRequest:
    try:
        value = json.loads(_read_private(path))
        if not isinstance(value, dict) or set(value) != {
            "bundle_path", "signature_path", "key_id", "evidence_path",
        }:
            raise ReleasePromotionOperatorInputRejected
        request = ReleasePromotionRequest(
            Path(_string(value["bundle_path"])),
            Path(_string(value["signature_path"])),
            _string(value["key_id"]),
            Path(_string(value["evidence_path"])),
        )
    except ReleasePromotionOperatorInputRejected:
        raise
    except Exception:
        raise ReleasePromotionOperatorInputRejected from None
    if request.signature_path.name != request.bundle_path.name + ".sshsig":
        raise ReleasePromotionOperatorInputRejected
    return request


def verify_promotion(
    request: ReleasePromotionRequest,
    projection: CurrentReleaseAuthorityRegistryProjection,
) -> bytes:
    evidence = verify_release_promotion_with_projection(
        bundle_path=request.bundle_path,
        signature_path=request.signature_path,
        registry_projection=projection,
        key_id=request.key_id,
    )
    return (
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def materialize_evidence(
    path: Path, evidence: bytes,
) -> MaterializedPromotionEvidence:
    if path.exists() or path.is_symlink():
        raise ReleasePromotionOperatorUnavailable
    try:
        parent = path.parent.stat()
    except OSError:
        raise ReleasePromotionOperatorUnavailable from None
    if not stat.S_ISDIR(parent.st_mode) or parent.st_mode & 0o077:
        raise ReleasePromotionOperatorUnavailable
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    )
    descriptor: int | None = None
    linked = False
    try:
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        written = 0
        while written < len(evidence):
            count = os.write(descriptor, evidence[written:])
            if count < 1:
                raise ReleasePromotionOperatorUnavailable
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, path)
        linked = True
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if linked:
            try:
                path.unlink()
            except OSError:
                pass
        raise ReleasePromotionOperatorUnavailable from None
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass
    return MaterializedPromotionEvidence(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-promotion")
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--verifier-id-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine: Engine | None = None
    try:
        request = load_request(args.request)
        database_url = _read_private(args.database_url_file).strip()
        verifier_id = ReleasePromotionVerifierId(
            _read_private(args.verifier_id_file).strip()
        )
        if not database_url:
            raise ReleasePromotionOperatorInputRejected
        engine = build_engine(database_url)
        projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
            engine, verification_identity=verifier_id
        )
        evidence = verify_promotion(request, projection)
        result = materialize_evidence(request.evidence_path, evidence)
    except ReleasePromotionOperatorInputRejected:
        _fail(ReleasePromotionOperatorInputRejected.code, 2)
    except PromotionRejected:
        _fail("release_promotion_operator_rejected", 3)
    except (PromotionUnavailable, ReleasePromotionOperatorUnavailable):
        _fail("release_promotion_operator_unavailable", 4)
    except Exception:
        _fail("release_promotion_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    sys.stdout.write('{"outcome":"verified"}\n')
    return 0
