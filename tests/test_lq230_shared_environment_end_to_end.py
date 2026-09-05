import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from liquent_platform.application.experiment import (
    ExperimentSnapshot,
    freeze_parameters,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.operators.initial_bootstrap import main as bootstrap_main
from liquent_platform.operators.membership_authority import (
    main as membership_authority_main,
)
from liquent_platform.operators.membership_authority_recovery import (
    main as membership_recovery_main,
)
from liquent_platform.operators.membership_management import (
    main as membership_main,
)
from liquent_platform.operators.oidc_trust_authority import (
    main as trust_authority_main,
)
from liquent_platform.operators.oidc_trust_authority_recovery import (
    main as trust_recovery_main,
)
from liquent_platform.operators.user_lifecycle import main as user_main
from liquent_platform.operators.workspace_lifecycle import main as workspace_main
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.transport.http.app import create_app

pytestmark = pytest.mark.postgres_integration

NOW = datetime.now(UTC)


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _apply(
    main: Callable[[list[str] | None], int],
    command: str,
    database: Path,
    directory: Path,
    name: str,
    payload: dict[str, Any],
) -> tuple[int, dict[str, Any] | None]:
    request = _private(
        directory / f"{name}-request.json", json.dumps(payload)
    )
    result = directory / f"{name}-result.json"
    exit_code = main([
        command, "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(result),
    ])
    value = (
        json.loads(result.read_text(encoding="utf-8"))
        if result.exists() else None
    )
    if value is not None:
        assert result.stat().st_mode & 0o777 == 0o600
    return exit_code, value


def _job(workspace_id: str) -> InMemoryResearchJob:
    return InMemoryResearchJob(
        JobId("lq230-job"),
        ExperimentSnapshot(
            experiment_id=ExperimentId("lq230-experiment"),
            workspace_id=WorkspaceId(workspace_id),
            title="LQ-230 protected research",
            dataset_ref="lq230-fixture.csv",
            dataset_fingerprint="sha256:lq230-fixture",
            strategy_version_id=StrategyVersionId("lq230-strategy"),
            strategy_parameters=freeze_parameters({}),
            risk_parameters=freeze_parameters({}),
            cost_parameters=freeze_parameters({}),
        ),
    )


def test_supported_multi_user_chain_reaches_and_revokes_runtime_access(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path
) -> None:
    database = _private(tmp_path / "database-url", postgres_url)
    bootstrap_result_path = tmp_path / "bootstrap-result.json"
    assert bootstrap_main([
        "identity", "--database-url-file", str(database),
        "--result-file", str(bootstrap_result_path),
    ]) == 0
    bootstrap = json.loads(
        bootstrap_result_path.read_text(encoding="utf-8")
    )

    code, user = _apply(
        user_main, "create", database, tmp_path, "create-user", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-create-user",
            "expected_revision": bootstrap["user_revision_id"],
        },
    )
    assert code == 0 and user is not None
    code, workspace = _apply(
        workspace_main, "create", database, tmp_path, "create-workspace", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-create-workspace",
            "initial_onboarding_manager_user_id": user["user_id"],
            "expected_revision": bootstrap["workspace_revision_id"],
        },
    )
    assert code == 0 and workspace is not None

    actor_file = _private(
        tmp_path / "actor-user-id", bootstrap["user_id"] + "\n"
    )
    trust_bootstrap_result = tmp_path / "trust-bootstrap-result.json"
    assert bootstrap_main([
        "oidc-trust-authority", "--database-url-file", str(database),
        "--user-id-file", str(actor_file), "--result-file",
        str(trust_bootstrap_result),
    ]) == 0
    code, trust_anchor = _apply(
        trust_authority_main, "anchor", database, tmp_path, "trust-anchor", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-trust-anchor",
        },
    )
    assert code == 0 and trust_anchor is not None

    code, membership_bootstrap = _apply(
        membership_main, "bootstrap-authority", database, tmp_path,
        "membership-bootstrap", {
            "user_id": bootstrap["user_id"],
            "workspace_id": bootstrap["workspace_id"],
        },
    )
    assert code == 0 and membership_bootstrap is not None
    code, membership_anchor = _apply(
        membership_authority_main, "anchor", database, tmp_path,
        "membership-anchor", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-membership-anchor",
            "workspace_id": bootstrap["workspace_id"],
        },
    )
    assert code == 0 and membership_anchor is not None

    code, trust_grant = _apply(
        trust_authority_main, "apply", database, tmp_path, "trust-grant", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-trust-grant",
            "target_user_id": user["user_id"],
            "intent": "grant",
            "expected_revision": trust_anchor["revision_id"],
        },
    )
    assert code == 0 and trust_grant is not None
    code, trust_rotated = _apply(
        trust_authority_main, "apply", database, tmp_path, "trust-deactivate", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-trust-deactivate",
            "target_user_id": bootstrap["user_id"],
            "intent": "deactivate",
            "expected_revision": trust_grant["revision_id"],
        },
    )
    assert code == 0 and trust_rotated is not None

    code, membership_grant = _apply(
        membership_authority_main, "apply", database, tmp_path,
        "membership-authority-grant", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-membership-authority-grant",
            "target_user_id": user["user_id"],
            "workspace_id": bootstrap["workspace_id"],
            "intent": "grant",
            "expected_revision": membership_anchor["revision_id"],
        },
    )
    assert code == 0 and membership_grant is not None
    code, membership_rotated = _apply(
        membership_authority_main, "apply", database, tmp_path,
        "membership-authority-deactivate", {
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq230-membership-authority-deactivate",
            "target_user_id": bootstrap["user_id"],
            "workspace_id": bootstrap["workspace_id"],
            "intent": "deactivate",
            "expected_revision": membership_grant["revision_id"],
        },
    )
    assert code == 0 and membership_rotated is not None

    code, membership = _apply(
        membership_main, "apply", database, tmp_path, "membership-active", {
            "actor_user_id": user["user_id"],
            "change_id": "lq230-membership-active",
            "target_user_id": user["user_id"],
            "workspace_id": bootstrap["workspace_id"],
            "expected_revision": None,
            "status": "active",
            "permissions": ["research:read", "research:write"],
        },
    )
    assert code == 0 and membership is not None

    sessions = DatabaseBrowserSessions(postgres_engine, now=lambda: NOW)
    session_id = SessionId("lq230-session")
    assert sessions.add_session(
        session_id,
        BrowserSessionRecord(
            ResolvedBrowserSession(
                SessionPrincipal(UserId(user["user_id"])), "lq230-csrf"
            ),
            NOW + timedelta(hours=1),
        ),
    )
    jobs = InMemoryResearchJobs()
    jobs.add(_job(bootstrap["workspace_id"]))
    app = create_app(
        PlatformSettings(_secrets_dir=None),
        database_engine=postgres_engine,
        research_jobs=jobs,
    )
    with TestClient(app) as client:
        client.cookies.set("liquent_session", str(session_id))
        allowed = client.get("/v1/research/jobs/lq230-job")
        assert allowed.status_code == 200

        code, revoked = _apply(
            membership_main, "apply", database, tmp_path,
            "membership-inactive", {
                "actor_user_id": user["user_id"],
                "change_id": "lq230-membership-inactive",
                "target_user_id": user["user_id"],
                "workspace_id": bootstrap["workspace_id"],
                "expected_revision": membership["revision_id"],
                "status": "inactive",
                "permissions": [],
            },
        )
        assert code == 0 and revoked is not None
        denied = client.get("/v1/research/jobs/lq230-job")
        assert denied.status_code == 404
        assert denied.json() == {"detail": "research_job_not_found"}

    code, result = _apply(
        trust_recovery_main, "recover", database, tmp_path, "trust-recovery", {
            "recovery_id": "lq230-trust-recovery",
            "target_user_id": bootstrap["user_id"],
            "expected_revision": trust_rotated["revision_id"],
        },
    )
    assert code == 5 and result is None
    code, result = _apply(
        membership_recovery_main, "recover", database, tmp_path,
        "membership-recovery", {
            "recovery_id": "lq230-membership-recovery",
            "target_user_id": bootstrap["user_id"],
            "workspace_id": bootstrap["workspace_id"],
            "expected_revision": membership_rotated["revision_id"],
        },
    )
    assert code == 5 and result is None
