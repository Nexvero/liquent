from inspect import signature

import pytest
from sqlalchemy import create_engine, text

from liquent_platform.identity.ports import ReleasePublicationExecutorRegistration
from liquent_platform.identity.release_publication import (
    RegisteredReleasePublicationExecutor,
    ReleasePublicationExecutorId,
    ReleasePublicationExecutorRegistrationId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationExecutorRegistrationUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_publication_executor_registration import (
    DatabaseReleasePublicationExecutorRegistration,
)


def _database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'registration.db'}")
    upgrade_to_head(str(engine.url))
    return engine


def test_port_accepts_only_stable_registration_id():
    parameters = list(signature(ReleasePublicationExecutorRegistration.register).parameters)
    assert parameters == ["self", "registration_id"]


def test_registration_creates_exactly_one_binding_and_retries_without_generation(tmp_path):
    engine = _database(tmp_path)
    calls = 0

    def generate():
        nonlocal calls
        calls += 1
        return ReleasePublicationExecutorId("executor-1")

    store = DatabaseReleasePublicationExecutorRegistration(
        engine, generate_executor_id=generate
    )
    request = ReleasePublicationExecutorRegistrationId("registration-1")

    first = store.register(request)
    second = store.register(request)

    assert first == second == RegisteredReleasePublicationExecutor(
        request, ReleasePublicationExecutorId("executor-1")
    )
    assert calls == 1
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_publication_executors")) == 1
        assert connection.scalar(text("SELECT count(*) FROM release_publication_executor_registrations")) == 1


def test_distinct_registration_ids_create_distinct_executors(tmp_path):
    engine = _database(tmp_path)
    generated = iter((ReleasePublicationExecutorId("executor-1"), ReleasePublicationExecutorId("executor-2")))
    store = DatabaseReleasePublicationExecutorRegistration(
        engine, generate_executor_id=lambda: next(generated)
    )

    first = store.register(ReleasePublicationExecutorRegistrationId("registration-1"))
    second = store.register(ReleasePublicationExecutorRegistrationId("registration-2"))

    assert first.executor_id != second.executor_id


@pytest.mark.parametrize("generated", [None, "executor-1"])
def test_invalid_generated_identity_rolls_back_detail_free(tmp_path, generated):
    engine = _database(tmp_path)
    store = DatabaseReleasePublicationExecutorRegistration(
        engine, generate_executor_id=lambda: generated
    )

    with pytest.raises(ReleasePublicationExecutorRegistrationUnavailable) as caught:
        store.register(ReleasePublicationExecutorRegistrationId("registration-1"))

    assert str(caught.value) == "release_publication_executor_registration_unavailable"
    assert caught.value.__cause__ is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_publication_executors")) == 0


def test_unmigrated_database_is_detail_free():
    store = DatabaseReleasePublicationExecutorRegistration(
        create_engine("sqlite://"),
        generate_executor_id=lambda: ReleasePublicationExecutorId("executor-1"),
    )

    with pytest.raises(ReleasePublicationExecutorRegistrationUnavailable) as caught:
        store.register(ReleasePublicationExecutorRegistrationId("registration-1"))

    assert str(caught.value) == "release_publication_executor_registration_unavailable"
    assert caught.value.__cause__ is None


def test_adapter_repr_discloses_no_engine_or_generator(tmp_path):
    store = DatabaseReleasePublicationExecutorRegistration(
        _database(tmp_path),
        generate_executor_id=lambda: ReleasePublicationExecutorId("secret-executor"),
    )
    assert repr(store) == "DatabaseReleasePublicationExecutorRegistration()"
