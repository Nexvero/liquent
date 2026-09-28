"""Owner-only offline operator for persistent release signing outputs."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.release_authority import (
    ReleaseRegistrySetRevisionId,
    ReleaseSigningDecisionId,
    ReleaseSigningExecutorId,
    ReleaseSigningKeyId,
    SignedReleaseCandidate,
)
from liquent_platform.operators.initial_bootstrap import _read_private
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleaseSigningConflict,
    ReleaseSigningUnavailable,
)
from liquent_platform.persistence.release_signing import DatabaseReleaseSigning


class ReleaseSigningOperatorInputRejected(Exception):
    code = "release_signing_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseSigningOperatorUnavailable(Exception):
    code = "release_signing_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleaseSigningRequest:
    decision_id: ReleaseSigningDecisionId = field(repr=False)
    key_id: ReleaseSigningKeyId = field(repr=False)
    expected_revision: ReleaseRegistrySetRevisionId = field(repr=False)
    bundle_path: Path = field(repr=False)
    signature_path: Path = field(repr=False)
    evidence_path: Path = field(repr=False)


@dataclass(frozen=True, slots=True)
class MaterializedSigningOutputs:
    signature_path: Path = field(repr=False)
    evidence_path: Path = field(repr=False)
    recovered: bool


def _string(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise ReleaseSigningOperatorInputRejected
    return value


def load_request(path: Path) -> ReleaseSigningRequest:
    try:
        value = json.loads(_read_private(path))
        if not isinstance(value, dict) or set(value) != {
            "decision_id", "key_id", "expected_revision", "bundle_path",
            "signature_path", "evidence_path",
        }:
            raise ReleaseSigningOperatorInputRejected
        request = ReleaseSigningRequest(
            ReleaseSigningDecisionId(_string(value["decision_id"])),
            ReleaseSigningKeyId(_string(value["key_id"])),
            ReleaseRegistrySetRevisionId(_string(value["expected_revision"])),
            Path(_string(value["bundle_path"])),
            Path(_string(value["signature_path"])),
            Path(_string(value["evidence_path"])),
        )
    except ReleaseSigningOperatorInputRejected:
        raise
    except Exception:
        raise ReleaseSigningOperatorInputRejected from None
    if (
        request.signature_path.name != request.bundle_path.name + ".sshsig"
        or request.evidence_path == request.signature_path
    ):
        raise ReleaseSigningOperatorInputRejected
    return request


def _regular_exact(path: Path, expected: bytes) -> bool:
    try:
        status = path.lstat()
        return (
            stat.S_ISREG(status.st_mode)
            and not stat.S_ISLNK(status.st_mode)
            and status.st_mode & 0o077 == 0
            and path.read_bytes() == expected
        )
    except OSError:
        return False


def _secure_parent(path: Path) -> None:
    try:
        status = path.parent.stat()
    except OSError:
        raise ReleaseSigningOperatorUnavailable from None
    if not stat.S_ISDIR(status.st_mode) or status.st_mode & 0o077:
        raise ReleaseSigningOperatorUnavailable


def _temporary(path: Path, value: bytes) -> Path:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        written = 0
        while written < len(value):
            count = os.write(descriptor, value[written:])
            if count < 1:
                raise ReleaseSigningOperatorUnavailable
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        return temporary
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except OSError:
            pass
        raise ReleaseSigningOperatorUnavailable from None


def materialize_outputs(
    request: ReleaseSigningRequest, result: SignedReleaseCandidate,
) -> MaterializedSigningOutputs:
    signature = request.signature_path
    evidence = request.evidence_path
    signature_exists = signature.exists() or signature.is_symlink()
    evidence_exists = evidence.exists() or evidence.is_symlink()
    if signature_exists or evidence_exists:
        if (
            signature_exists and evidence_exists
            and _regular_exact(signature, result.signature)
            and _regular_exact(evidence, result.evidence)
        ):
            return MaterializedSigningOutputs(signature, evidence, True)
        raise ReleaseSigningOperatorUnavailable
    _secure_parent(signature)
    _secure_parent(evidence)
    signature_temp = _temporary(signature, result.signature)
    evidence_temp: Path | None = None
    linked: list[Path] = []
    try:
        evidence_temp = _temporary(evidence, result.evidence)
        os.link(signature_temp, signature)
        linked.append(signature)
        os.link(evidence_temp, evidence)
        linked.append(evidence)
        for parent in {signature.parent, evidence.parent}:
            descriptor = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except Exception:
        for path in reversed(linked):
            try:
                path.unlink()
            except OSError:
                pass
        raise ReleaseSigningOperatorUnavailable from None
    finally:
        for path in (signature_temp, evidence_temp):
            if path is not None:
                try:
                    path.unlink()
                except OSError:
                    pass
    return MaterializedSigningOutputs(signature, evidence, False)


class OpenSshSigningKeyProvider:
    __slots__ = ("_private_key", "_ssh_keygen")

    def __init__(self, private_key: Path, ssh_keygen: str = "ssh-keygen") -> None:
        _read_private(private_key)
        self._private_key = private_key
        self._ssh_keygen = ssh_keygen

    def fingerprint(self) -> str:
        try:
            return subprocess.run(
                [self._ssh_keygen, "-lf", str(self._private_key), "-E", "sha256"],
                check=True, capture_output=True, text=True,
            ).stdout.split()[1]
        except Exception:
            raise ReleaseSigningOperatorUnavailable from None

    def sign(self, payload: bytes, namespace: str) -> bytes:
        try:
            with tempfile.TemporaryDirectory(prefix="liquent-signing-provider-") as root:
                payload_path = Path(root) / "SHA256SUMS"
                payload_path.write_bytes(payload)
                subprocess.run(
                    [self._ssh_keygen, "-Y", "sign", "-f", str(self._private_key),
                     "-n", namespace, str(payload_path)],
                    check=True, capture_output=True,
                )
                signature = payload_path.with_suffix(".sig").read_bytes()
            return signature
        except Exception:
            raise ReleaseSigningOperatorUnavailable from None


class OpenSshReleaseSignatureVerifier:
    __slots__ = ("_ssh_keygen",)

    def __init__(self, ssh_keygen: str = "ssh-keygen") -> None:
        self._ssh_keygen = ssh_keygen

    def verify(self, public_key, authority_id, payload, signature) -> bool:
        try:
            with tempfile.TemporaryDirectory(prefix="liquent-signing-verify-") as root:
                directory = Path(root)
                allowed = directory / "allowed_signers"
                signed = directory / "candidate.sshsig"
                allowed.write_text(
                    f'{authority_id} namespaces="liquent-operations-release-v1" {public_key}\n',
                    encoding="ascii",
                )
                signed.write_bytes(signature)
                result = subprocess.run(
                    [self._ssh_keygen, "-Y", "verify", "-f", str(allowed),
                     "-I", authority_id, "-n", "liquent-operations-release-v1",
                     "-s", str(signed)],
                    input=payload, capture_output=True,
                )
            return result.returncode == 0
        except Exception:
            raise ReleaseSigningOperatorUnavailable from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-signing")
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--executor-id-file", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
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
        executor = ReleaseSigningExecutorId(_read_private(args.executor_id_file).strip())
        if not database_url:
            raise ReleaseSigningOperatorInputRejected
        engine = build_engine(database_url)
        result = DatabaseReleaseSigning(
            engine, executor_id=executor,
            key_provider=OpenSshSigningKeyProvider(args.private_key),
            signature_verifier=OpenSshReleaseSignatureVerifier(),
        ).sign_candidate(
            request.decision_id, request.key_id, request.expected_revision,
            str(request.bundle_path),
        )
        outputs = None if result is None else materialize_outputs(request, result)
    except ReleaseSigningOperatorInputRejected:
        _fail(ReleaseSigningOperatorInputRejected.code, 2)
    except ReleaseSigningConflict:
        _fail("release_signing_operator_conflict", 3)
    except (ReleaseSigningUnavailable, ReleaseSigningOperatorUnavailable):
        _fail("release_signing_operator_unavailable", 4)
    except Exception:
        _fail("release_signing_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        sys.stdout.write('{"outcome":"rejected"}\n')
        return 5
    sys.stdout.write(json.dumps({
        "outcome": "recovered" if outputs.recovered else "signed",
        "decision_id": result.decision_id.value,
    }, separators=(",", ":")) + "\n")
    return 0
