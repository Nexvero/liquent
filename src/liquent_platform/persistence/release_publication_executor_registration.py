"""Atomic persistent registration of technical publication executors."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.release_publication import (
    RegisteredReleasePublicationExecutor,
    ReleasePublicationExecutorId,
    ReleasePublicationExecutorRegistrationId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationExecutorRegistrationUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_publication_executors,"
    " release_publication_executor_registrations IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT executor_id FROM release_publication_executor_registrations"
    " WHERE registration_id=:registration"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise ReleasePublicationExecutorRegistrationUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationExecutorRegistrationUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReleasePublicationExecutorRegistrationUnavailable from error


class DatabaseReleasePublicationExecutorRegistration:
    """Bind one stable registration request to one internal executor identity."""

    __slots__ = ("_engine", "_generate_executor_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_executor_id: Callable[[], ReleasePublicationExecutorId],
    ) -> None:
        self._engine = engine
        self._generate_executor_id = generate_executor_id

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationExecutorRegistration()"

    def register(
        self, registration_id: ReleasePublicationExecutorRegistrationId
    ) -> RegisteredReleasePublicationExecutor:
        try:
            if type(registration_id) is not ReleasePublicationExecutorRegistrationId:
                raise ReleasePublicationExecutorRegistrationUnavailable
            values = {"registration": _encode(registration_id.value)}
            with self._engine.begin() as transaction:
                return self._register(transaction, registration_id, values)
        except ReleasePublicationExecutorRegistrationUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationExecutorRegistrationUnavailable

    def _register(
        self,
        transaction: Connection,
        registration_id: ReleasePublicationExecutorRegistrationId,
        values: dict[str, bytes],
    ) -> RegisteredReleasePublicationExecutor:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleasePublicationExecutorRegistrationUnavailable

        existing = transaction.execute(_EXISTING, values).scalar_one_or_none()
        if existing is not None:
            return RegisteredReleasePublicationExecutor(
                registration_id, ReleasePublicationExecutorId(_decode(existing))
            )

        executor_id = self._generate_executor_id()
        if type(executor_id) is not ReleasePublicationExecutorId:
            raise ReleasePublicationExecutorRegistrationUnavailable
        values["executor"] = _encode(executor_id.value)
        transaction.execute(
            text("INSERT INTO release_publication_executors VALUES (:executor)"),
            values,
        )
        transaction.execute(
            text(
                "INSERT INTO release_publication_executor_registrations"
                " (registration_id,executor_id) VALUES (:registration,:executor)"
            ),
            values,
        )
        return RegisteredReleasePublicationExecutor(registration_id, executor_id)
