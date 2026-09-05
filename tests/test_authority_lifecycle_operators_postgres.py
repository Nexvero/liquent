import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.operators.membership_authority import (
    main as membership_main,
)
from liquent_platform.operators.oidc_trust_authority import main as oidc_main

pytestmark = pytest.mark.postgres_integration


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_both_offline_operator_chains_run_on_postgresql(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path
) -> None:
    actor = "operator-215-postgres-actor"
    target = "operator-215-postgres-target"
    workspace = "operator-215-postgres-workspace"
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:actor,'active'),(:target,'active')"
        ), {"actor": actor.encode(), "target": target.encode()})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": workspace.encode()})
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:actor,'active')"
        ), {"actor": actor.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": actor.encode(), "workspace": workspace.encode()})
    database = _private(tmp_path / "database-url", postgres_url)

    oidc_anchor_request = _private(tmp_path / "oidc-anchor.json", json.dumps({
        "actor_user_id": actor, "change_id": "operator-215-oidc-anchor",
    }))
    oidc_anchor_result = tmp_path / "oidc-anchor-result.json"
    assert oidc_main([
        "anchor", "--database-url-file", str(database), "--request",
        str(oidc_anchor_request), "--result-file", str(oidc_anchor_result),
    ]) == 0
    oidc_revision = json.loads(
        oidc_anchor_result.read_text(encoding="utf-8")
    )["revision_id"]
    oidc_change = _private(tmp_path / "oidc-change.json", json.dumps({
        "actor_user_id": actor,
        "change_id": "operator-215-oidc-grant",
        "target_user_id": target,
        "intent": "grant",
        "expected_revision": oidc_revision,
    }))
    assert oidc_main([
        "apply", "--database-url-file", str(database), "--request",
        str(oidc_change), "--result-file", str(tmp_path / "oidc-change-result.json"),
    ]) == 0

    membership_anchor = _private(
        tmp_path / "membership-anchor.json", json.dumps({
            "actor_user_id": actor,
            "change_id": "operator-215-membership-anchor",
            "workspace_id": workspace,
        })
    )
    membership_anchor_result = tmp_path / "membership-anchor-result.json"
    assert membership_main([
        "anchor", "--database-url-file", str(database), "--request",
        str(membership_anchor), "--result-file", str(membership_anchor_result),
    ]) == 0
    membership_revision = json.loads(
        membership_anchor_result.read_text(encoding="utf-8")
    )["revision_id"]
    membership_change = _private(
        tmp_path / "membership-change.json", json.dumps({
            "actor_user_id": actor,
            "change_id": "operator-215-membership-grant",
            "target_user_id": target,
            "workspace_id": workspace,
            "intent": "grant",
            "expected_revision": membership_revision,
        })
    )
    assert membership_main([
        "apply", "--database-url-file", str(database), "--request",
        str(membership_change), "--result-file",
        str(tmp_path / "membership-change-result.json"),
    ]) == 0
