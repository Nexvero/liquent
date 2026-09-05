from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import ProvisioningRequestId
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OnboardingDecisionConflict,
    OnboardingDecisionStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.onboarding_decision import (
    DatabaseAuthorizedOnboardingDecisions,
)

DECISION = OnboardingDecisionId("decision-1")
REQUEST = ProvisioningRequestId("request-1")
ACTOR = UserId("actor-1")
TARGET = UserId("target-1")
WORKSPACE = WorkspaceId("workspace-1")


class Source:
    def __init__(self, value: Any) -> None:
        self.value, self.calls = value, 0

    def __call__(self) -> Any:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'decision.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine, *, authority: str = "active") -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_users (user_id, status)"
                " VALUES (:actor, 'active'), (:target, 'active')"
            ),
            {"actor": ACTOR.encode(), "target": TARGET.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id, status)"
                " VALUES (:workspace, 'active')"
            ),
            {"workspace": WORKSPACE.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_onboarding_management"
                " (user_id, workspace_id, status)"
                " VALUES (:actor, :workspace, :status)"
            ),
            {
                "actor": ACTOR.encode(),
                "workspace": WORKSPACE.encode(),
                "status": authority,
            },
        )


def _store(
    engine: Engine, source: Source | None = None
) -> DatabaseAuthorizedOnboardingDecisions:
    return DatabaseAuthorizedOnboardingDecisions(
        engine, generate_provisioning_request_id=source or Source(REQUEST)
    )


def _decide(store: DatabaseAuthorizedOnboardingDecisions, target: UserId = TARGET):
    return store.decide(DECISION, SessionPrincipal(ACTOR), target, WORKSPACE)


def test_authorized_decision_is_persisted_with_generated_request(
    engine: Engine,
) -> None:
    _foundation(engine)
    source = Source(REQUEST)

    result = _decide(_store(engine, source))

    assert result is not None
    assert result.provisioning_request_id == REQUEST
    assert source.calls == 1


def test_exact_retry_recovers_same_request_without_authority_or_generator(
    engine: Engine,
) -> None:
    _foundation(engine)
    assert _decide(_store(engine)) is not None
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE workspace_onboarding_management SET status='inactive'")
        )
    source = Source(ProvisioningRequestId("request-2"))

    repeated = _decide(_store(engine, source))

    assert repeated is not None
    assert repeated.provisioning_request_id == REQUEST
    assert source.calls == 0


def test_same_decision_with_changed_target_is_conflict(engine: Engine) -> None:
    _foundation(engine)
    assert _decide(_store(engine)) is not None

    with pytest.raises(OnboardingDecisionConflict):
        _decide(_store(engine), UserId("other-target"))


@pytest.mark.parametrize("authority", ["inactive", None])
def test_missing_or_revoked_authority_is_neutral_and_does_not_generate(
    engine: Engine, authority: str | None
) -> None:
    if authority is None:
        _foundation(engine)
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM workspace_onboarding_management"))
    else:
        _foundation(engine, authority=authority)
    source = Source(REQUEST)

    assert _decide(_store(engine, source)) is None
    assert source.calls == 0


def test_generator_failure_rolls_back_decision(engine: Engine) -> None:
    _foundation(engine)
    with pytest.raises(OnboardingDecisionStoreUnavailable):
        _decide(_store(engine, Source(RuntimeError("generator"))))
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM authorized_onboarding_decisions")
        ) == 0


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(engine)
    try:
        with pytest.raises(OnboardingDecisionStoreUnavailable) as raised:
            _decide(store)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseAuthorizedOnboardingDecisions()"
    finally:
        engine.dispose()
