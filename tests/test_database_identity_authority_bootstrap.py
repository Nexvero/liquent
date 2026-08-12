from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.bootstrap import BootstrappedIdentityAuthority
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseIdentityAuthorityBootstrapStore,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)


class Source:
    def __init__(self, value: Any) -> None:
        self.value, self.calls = value, 0

    def __call__(self) -> Any:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


@pytest.fixture
def engine(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'bootstrap-store.db'}"
    upgrade_to_head(url)
    built = build_engine(url)
    yield built
    built.dispose()


def _store(engine: Any, values: tuple[Any, Any, Any, Any, Any]):
    sources = tuple(Source(value) for value in values)
    user, workspace, request, admission, clock = sources
    return (
        DatabaseIdentityAuthorityBootstrapStore(
            engine,
            generate_user_id=user,
            generate_workspace_id=workspace,
            generate_request_id=request,
            generate_admission_id=admission,
            now=clock,
            admission_lifetime=timedelta(hours=1),
        ),
        sources,
    )


def test_portable_first_transition_and_exact_replay(engine: Any) -> None:
    values = (
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        ProvisioningRequestId("request-1"),
        IdentityAdmissionId("admission-1"),
        NOW,
    )
    store, sources = _store(engine, values)
    expected = BootstrappedIdentityAuthority(values[0], values[1], values[3])

    assert store.bootstrap_initial_identity() == expected
    assert [source.calls for source in sources] == [1, 1, 1, 1, 1]
    blocked, blocked_sources = _store(
        engine, tuple(AssertionError("must not run") for _ in range(5))
    )
    assert blocked.bootstrap_initial_identity() == expected
    assert [source.calls for source in blocked_sources] == [0, 0, 0, 0, 0]


@pytest.mark.parametrize(
    "lifetime",
    [timedelta(0), timedelta(microseconds=-1), timedelta(microseconds=0.4), 1],
)
def test_invalid_lifetime_is_rejected_at_construction(
    engine: Any, lifetime: object
) -> None:
    values = tuple(Source(AssertionError("must not run")) for _ in range(5))
    with pytest.raises(ValueError) as rejected:
        DatabaseIdentityAuthorityBootstrapStore(
            engine,
            generate_user_id=values[0],
            generate_workspace_id=values[1],
            generate_request_id=values[2],
            generate_admission_id=values[3],
            now=values[4],
            admission_lifetime=lifetime,  # type: ignore[arg-type]
        )
    assert rejected.value.args == ("invalid admission lifetime",)
    assert all(source.calls == 0 for source in values)


def test_unexpected_error_is_neutral_and_base_exception_propagates(engine: Any) -> None:
    dirty = IdentityAuthorityBootstrapUnavailable()
    try:
        raise RuntimeError("SECRET")
    except RuntimeError:
        try:
            raise dirty
        except IdentityAuthorityBootstrapUnavailable as captured:
            dirty = captured
    store, _ = _store(engine, (dirty, None, None, None, None))
    with pytest.raises(IdentityAuthorityBootstrapUnavailable) as neutral:
        store.bootstrap_initial_identity()
    assert neutral.value is not dirty
    assert neutral.value.__cause__ is neutral.value.__context__ is None

    raw = KeyboardInterrupt()
    store, _ = _store(engine, (raw, None, None, None, None))
    with pytest.raises(KeyboardInterrupt) as propagated:
        store.bootstrap_initial_identity()
    assert propagated.value is raw


def test_repr_exposes_no_engine_or_generated_material(engine: Any) -> None:
    store, _ = _store(engine, ("SECRET",) * 5)
    assert repr(store) == "DatabaseIdentityAuthorityBootstrapStore()"
