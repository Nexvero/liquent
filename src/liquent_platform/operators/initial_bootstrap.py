"""Controlled offline access to the two one-time bootstrap boundaries."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn, TextIO

from sqlalchemy import Engine, text

from liquent_platform.identity.access import BootstrappedIdentityAuthority, UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.oidc_trust import BootstrappedOidcTrustAuthority
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
    OidcTrustAuthorityBootstrapUnavailable,
)
from liquent_platform.persistence.oidc_trust_bootstrap import (
    DatabaseInitialOidcTrustAuthorityBootstrap,
)


class InitialBootstrapOperatorUnavailable(Exception):
    """A detail-free process-boundary failure."""

    code = "initial_bootstrap_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class RecoveredIdentityBootstrap:
    result: BootstrappedIdentityAuthority = field(repr=False)
    user_revision_id: UserLifecycleRevisionId = field(repr=False)
    workspace_revision_id: WorkspaceLifecycleRevisionId = field(repr=False)
    recovered: bool


@dataclass(frozen=True, slots=True)
class RecoveredOidcTrustAuthorityBootstrap:
    result: BootstrappedOidcTrustAuthority = field(repr=False)
    recovered: bool


def _read_private(path: Path) -> str:
    try:
        if path.is_symlink():
            raise InitialBootstrapOperatorUnavailable
        status = path.stat()
        if not stat.S_ISREG(status.st_mode) or status.st_mode & 0o077:
            raise InitialBootstrapOperatorUnavailable
        value = path.read_text(encoding="utf-8")
    except InitialBootstrapOperatorUnavailable:
        raise
    except (OSError, UnicodeError):
        raise InitialBootstrapOperatorUnavailable from None
    if not value or "\x00" in value:
        raise InitialBootstrapOperatorUnavailable
    return value


def _decode(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise InitialBootstrapOperatorUnavailable
    try:
        decoded = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise InitialBootstrapOperatorUnavailable from None
    if not decoded:
        raise InitialBootstrapOperatorUnavailable
    return decoded


def _recover_identity(
    engine: Engine,
) -> tuple[
    BootstrappedIdentityAuthority,
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
] | None:
    with engine.connect() as connection:
        counts = connection.execute(text(
            "SELECT (SELECT count(*) FROM identity_users),"
            " (SELECT count(*) FROM identity_workspaces),"
            " (SELECT count(*) FROM workspace_onboarding_management),"
            " (SELECT count(*) FROM user_lifecycle_management_authorities),"
            " (SELECT count(*) FROM workspace_lifecycle_management_authorities),"
            " (SELECT count(*) FROM user_lifecycle_revisions),"
            " (SELECT count(*) FROM user_lifecycle_revision_members),"
            " (SELECT count(*) FROM user_lifecycle_current_revision),"
            " (SELECT count(*) FROM user_lifecycle_changes),"
            " (SELECT count(*) FROM workspace_lifecycle_revisions),"
            " (SELECT count(*) FROM workspace_lifecycle_revision_members),"
            " (SELECT count(*) FROM workspace_lifecycle_current_revision),"
            " (SELECT count(*) FROM workspace_lifecycle_changes),"
            " (SELECT count(*) FROM user_lifecycle_authority_set_revisions),"
            " (SELECT count(*) FROM user_lifecycle_authority_set_members),"
            " (SELECT count(*) FROM user_lifecycle_authority_current_set),"
            " (SELECT count(*) FROM user_lifecycle_authority_changes),"
            " (SELECT count(*) FROM workspace_lifecycle_authority_set_revisions),"
            " (SELECT count(*) FROM workspace_lifecycle_authority_set_members),"
            " (SELECT count(*) FROM workspace_lifecycle_authority_current_set),"
            " (SELECT count(*) FROM workspace_lifecycle_authority_changes)"
        )).one()
        if counts != (
            1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
        ):
            return None
        row = connection.execute(text(
            "SELECT users.user_id,workspaces.workspace_id,"
            " user_current.revision_id AS user_revision_id,"
            " workspace_current.revision_id AS workspace_revision_id"
            " FROM identity_users AS users"
            " JOIN workspace_onboarding_management AS authority"
            " ON authority.user_id=users.user_id"
            " JOIN identity_workspaces AS workspaces"
            " ON workspaces.workspace_id=authority.workspace_id"
            " JOIN user_lifecycle_management_authorities AS user_authority"
            " ON user_authority.user_id=users.user_id"
            " JOIN workspace_lifecycle_management_authorities AS workspace_authority"
            " ON workspace_authority.user_id=users.user_id"
            " JOIN user_lifecycle_revision_members AS user_member"
            " ON user_member.user_id=users.user_id"
            " JOIN user_lifecycle_current_revision AS user_current"
            " ON user_current.revision_id=user_member.revision_id"
            " JOIN workspace_lifecycle_revision_members AS workspace_member"
            " ON workspace_member.workspace_id=workspaces.workspace_id"
            " JOIN workspace_lifecycle_current_revision AS workspace_current"
            " ON workspace_current.revision_id=workspace_member.revision_id"
            " WHERE users.status='active' AND workspaces.status='active'"
            " AND authority.status='active' AND user_authority.status='active'"
            " AND workspace_authority.status='active'"
            " AND user_member.status='active' AND workspace_member.status='active'"
        )).first()
    if row is None:
        return None
    return (
        BootstrappedIdentityAuthority(
            UserId(_decode(row.user_id)), WorkspaceId(_decode(row.workspace_id))
        ),
        UserLifecycleRevisionId(_decode(row.user_revision_id)),
        WorkspaceLifecycleRevisionId(_decode(row.workspace_revision_id)),
    )


def bootstrap_identity(
    engine: Engine, material: SecureIdentityAuthorityMaterialGenerator
) -> RecoveredIdentityBootstrap | None:
    user_revisions: list[UserLifecycleRevisionId] = []
    workspace_revisions: list[WorkspaceLifecycleRevisionId] = []

    def user_revision() -> UserLifecycleRevisionId:
        value = material.new_user_lifecycle_revision_id()
        user_revisions.append(value)
        return value

    def workspace_revision() -> WorkspaceLifecycleRevisionId:
        value = material.new_workspace_lifecycle_revision_id()
        workspace_revisions.append(value)
        return value

    store = DatabaseInitialIdentityAuthorityBootstrap(
        engine,
        generate_user_id=material.new_user_id,
        generate_workspace_id=material.new_workspace_id,
        generate_user_revision_id=user_revision,
        generate_workspace_revision_id=workspace_revision,
    )
    created = store.bootstrap()
    if created is not None:
        if len(user_revisions) != 1 or len(workspace_revisions) != 1:
            raise IdentityAuthorityBootstrapUnavailable
        return RecoveredIdentityBootstrap(
            created, user_revisions[0], workspace_revisions[0], False
        )
    recovered = _recover_identity(engine)
    if recovered is None:
        return None
    result, recovered_user_revision, recovered_workspace_revision = recovered
    return RecoveredIdentityBootstrap(
        result, recovered_user_revision, recovered_workspace_revision, True
    )


def _recover_trust_authority(
    engine: Engine, user_id: UserId
) -> BootstrappedOidcTrustAuthority | None:
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT authority.user_id FROM oidc_trust_management_authorities"
            " AS authority JOIN identity_users AS users"
            " ON users.user_id=authority.user_id"
            " WHERE authority.status='active' AND users.status='active'"
        )).all()
        count = connection.scalar(text(
            "SELECT count(*) FROM oidc_trust_management_authorities"
        ))
    expected = str(user_id).encode("utf-8")
    if count != 1 or len(rows) != 1 or bytes(rows[0].user_id) != expected:
        return None
    return BootstrappedOidcTrustAuthority(user_id)


def bootstrap_oidc_trust_authority(
    engine: Engine, user_id: UserId
) -> RecoveredOidcTrustAuthorityBootstrap | None:
    created = DatabaseInitialOidcTrustAuthorityBootstrap(engine).bootstrap(user_id)
    if created is not None:
        return RecoveredOidcTrustAuthorityBootstrap(created, False)
    recovered = _recover_trust_authority(engine, user_id)
    return (
        None
        if recovered is None
        else RecoveredOidcTrustAuthorityBootstrap(recovered, True)
    )


def _write_result(path: Path, payload: dict[str, str]) -> None:
    if path.exists() or path.is_symlink():
        raise InitialBootstrapOperatorUnavailable
    try:
        parent_status = path.parent.stat()
    except OSError:
        raise InitialBootstrapOperatorUnavailable from None
    if not stat.S_ISDIR(parent_status.st_mode) or parent_status.st_mode & 0o077:
        raise InitialBootstrapOperatorUnavailable
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        data = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        written = 0
        while written < len(data):
            count = os.write(descriptor, data[written:])
            if count < 1:
                raise InitialBootstrapOperatorUnavailable
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except OSError:
            pass
        raise InitialBootstrapOperatorUnavailable from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-initial-bootstrap")
    commands = parser.add_subparsers(dest="command", required=True)
    identity = commands.add_parser("identity")
    trust = commands.add_parser("oidc-trust-authority")
    for command in (identity, trust):
        command.add_argument("--database-url-file", required=True, type=Path)
        command.add_argument("--result-file", required=True, type=Path)
    trust.add_argument("--user-id-file", required=True, type=Path)
    return parser


def _emit(stream: TextIO, value: str) -> None:
    stream.write(json.dumps({"outcome": value}, separators=(",", ":")) + "\n")


def _fail(code: str, exit_code: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise InitialBootstrapOperatorUnavailable
        engine = build_engine(database_url)
        if args.command == "identity":
            outcome = bootstrap_identity(
                engine, SecureIdentityAuthorityMaterialGenerator()
            )
            if outcome is not None:
                _write_result(args.result_file, {
                    "user_id": str(outcome.result.user_id),
                    "workspace_id": str(outcome.result.workspace_id),
                    "user_revision_id": outcome.user_revision_id.value,
                    "workspace_revision_id": outcome.workspace_revision_id.value,
                })
        else:
            user_value = _read_private(args.user_id_file)
            if user_value.endswith("\n"):
                user_value = user_value[:-1]
            if not user_value or "\n" in user_value or "\r" in user_value:
                raise InitialBootstrapOperatorUnavailable
            outcome = bootstrap_oidc_trust_authority(engine, UserId(user_value))
            if outcome is not None:
                _write_result(args.result_file, {"user_id": user_value})
    except (IdentityAuthorityBootstrapUnavailable,
            OidcTrustAuthorityBootstrapUnavailable,
            InitialBootstrapOperatorUnavailable):
        _fail(InitialBootstrapOperatorUnavailable.code, 2)
    except Exception:
        _fail(InitialBootstrapOperatorUnavailable.code, 2)
    finally:
        if engine is not None:
            engine.dispose()

    if outcome is None:
        _emit(sys.stdout, "closed")
        return 5
    _emit(sys.stdout, "recovered" if outcome.recovered else "bootstrapped")
    return 0
