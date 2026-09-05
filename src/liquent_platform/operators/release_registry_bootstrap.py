"""Owner-only offline process for the one-time release-registry bootstrap."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_authority import (
    ReleaseRegistryBootstrapId,
    ReleaseSigningPublicKey,
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
    ReleaseRegistryBootstrapConflict,
    ReleaseRegistryBootstrapUnavailable,
)
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


class ReleaseRegistryBootstrapOperatorInputRejected(Exception):
    code = "release_registry_bootstrap_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseRegistryBootstrapOperatorUnavailable(Exception):
    code = "release_registry_bootstrap_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _input(action):
    try:
        return action()
    except ReleasePublicationOperatorInputRejected:
        raise ReleaseRegistryBootstrapOperatorInputRejected from None
    except ReleasePublicationOperatorUnavailable:
        raise ReleaseRegistryBootstrapOperatorUnavailable from None


def load_request(path: Path) -> ReleaseRegistryBootstrapId:
    value = _input(lambda: _json_file(path, {"bootstrap_id"}))
    try:
        return ReleaseRegistryBootstrapId(_string(value["bootstrap_id"]))
    except Exception:
        raise ReleaseRegistryBootstrapOperatorInputRejected from None


def load_public_key(path: Path, ssh_keygen: str = "ssh-keygen") -> ReleaseSigningPublicKey:
    value = _input(lambda: _private_text(path, 8192))
    if value.endswith("\n"):
        value = value[:-1]
    if "\n" in value or len(value.split()) != 2 or not value.startswith("ssh-ed25519 "):
        raise ReleaseRegistryBootstrapOperatorInputRejected
    try:
        with tempfile.TemporaryDirectory(prefix="liquent-registry-bootstrap-") as root:
            public = Path(root) / "key.pub"
            public.write_text(value + "\n", encoding="ascii")
            os.chmod(public, 0o600)
            fingerprint = subprocess.run(
                [ssh_keygen, "-lf", str(public), "-E", "sha256"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()[1]
        return ReleaseSigningPublicKey(fingerprint, value)
    except (ValueError, UnicodeError):
        raise ReleaseRegistryBootstrapOperatorInputRejected from None
    except Exception:
        raise ReleaseRegistryBootstrapOperatorUnavailable from None


def run_operator(
    *, database_url_file: Path, request_file: Path, public_key_file: Path,
):
    bootstrap_id = load_request(request_file)
    public_key = load_public_key(public_key_file)
    database_url = _input(lambda: _private_text(database_url_file, 8192))
    if database_url.endswith("\n"):
        database_url = database_url[:-1]
    try:
        database_url = _string(database_url)
    except Exception:
        raise ReleaseRegistryBootstrapOperatorInputRejected from None
    engine = None
    try:
        engine = build_engine(database_url)
        if not DatabaseReadinessProbe(engine).check().ready:
            raise ReleaseRegistryBootstrapOperatorUnavailable
        material = SecureIdentityAuthorityMaterialGenerator()
        return DatabaseInitialReleaseRegistryBootstrap(
            engine,
            generate_lifecycle_authority_id=(
                material.new_release_registry_lifecycle_authority_id
            ),
            generate_signer_authority_id=material.new_release_signer_authority_id,
            generate_key_id=material.new_release_signing_key_id,
            generate_registry_revision_id=material.new_release_registry_set_revision_id,
            generate_policy_revision_id=material.new_release_policy_revision_id,
        ).bootstrap(bootstrap_id, public_key)
    except ReleaseRegistryBootstrapOperatorUnavailable:
        raise
    except ReleaseRegistryBootstrapConflict:
        raise
    except ReleaseRegistryBootstrapUnavailable:
        raise ReleaseRegistryBootstrapOperatorUnavailable from None
    except Exception:
        raise ReleaseRegistryBootstrapOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-release-registry-bootstrap")
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--public-key-file", required=True, type=Path)
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
            public_key_file=arguments.public_key_file,
        )
    except ReleaseRegistryBootstrapOperatorInputRejected:
        _fail(ReleaseRegistryBootstrapOperatorInputRejected.code, 2)
    except ReleaseRegistryBootstrapConflict:
        _fail("release_registry_bootstrap_operator_conflict", 3)
    except Exception:
        _fail(ReleaseRegistryBootstrapOperatorUnavailable.code, 4)
    if result is None:
        sys.stdout.write('{"outcome":"not_bootstrapped"}\n')
        return 5
    sys.stdout.write(json.dumps({
        "bootstrap_id": result.bootstrap_id.value,
        "key_id": result.key_id.value,
        "lifecycle_authority_id": result.lifecycle_authority_id.value,
        "outcome": "bootstrapped",
        "policy_revision_id": result.policy_revision_id.value,
        "registry_revision_id": result.registry_revision_id.value,
        "signer_authority_id": result.signer_authority_id.value,
    }, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
