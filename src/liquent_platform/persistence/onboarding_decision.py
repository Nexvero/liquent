"""Atomic authorization and persistence of immutable onboarding decisions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import ProvisioningRequestId
from liquent_platform.identity.onboarding import (
    AuthorizedOnboardingDecision,
    OnboardingDecisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    OnboardingDecisionConflict,
    OnboardingDecisionStoreUnavailable,
)

_SELECT_DECISION = text(
    "SELECT provisioning_request, actor_user_id, target_user_id,"
    " target_workspace_id FROM authorized_onboarding_decisions"
    " WHERE decision_id=:decision"
)
_PERMITS_POSTGRES = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_onboarding_management AS authority"
    " ON authority.user_id=actor.user_id"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " JOIN identity_users AS target ON target.user_id=:target"
    " WHERE actor.user_id=:actor AND workspace.workspace_id=:workspace"
    " AND actor.status='active' AND target.status='active'"
    " AND workspace.status='active' AND authority.status='active'"
    " FOR UPDATE OF actor, target, workspace, authority"
)
_PERMITS_SQLITE = text(str(_PERMITS_POSTGRES).replace(
    " FOR UPDATE OF actor, target, workspace, authority", ""
))
_INSERT_DECISION = text(
    "INSERT INTO authorized_onboarding_decisions"
    " (decision_id, provisioning_request, actor_user_id, target_user_id,"
    " target_workspace_id) VALUES (:decision, :request, :actor, :target,"
    " :workspace)"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OnboardingDecisionStoreUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise OnboardingDecisionStoreUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        result = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OnboardingDecisionStoreUnavailable from None
    if not result:
        raise OnboardingDecisionStoreUnavailable
    return result


class DatabaseAuthorizedOnboardingDecisions:
    """Persist one currently authorized decision and resolve exact retries."""

    __slots__ = ("_engine", "_generate_request_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_provisioning_request_id: Callable[[], ProvisioningRequestId],
    ) -> None:
        self._engine = engine
        self._generate_request_id = generate_provisioning_request_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedOnboardingDecisions()"

    def decide(
        self,
        decision_id: OnboardingDecisionId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> AuthorizedOnboardingDecision | None:
        try:
            return self._decide(
                decision_id, principal, target_user_id, target_workspace_id
            )
        except OnboardingDecisionConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = OnboardingDecisionConflict
        except OnboardingDecisionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = OnboardingDecisionStoreUnavailable
        except Exception:
            failure = OnboardingDecisionStoreUnavailable
        raise failure()

    def _decide(
        self,
        decision_id: OnboardingDecisionId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> AuthorizedOnboardingDecision | None:
        decision = _encode(decision_id.value)
        actor = _encode(principal.user_id)
        target = _encode(target_user_id)
        workspace = _encode(target_workspace_id)

        with self._engine.begin() as transaction:
            existing = transaction.execute(
                _SELECT_DECISION, {"decision": decision}
            ).first()
            if existing is not None:
                return self._resolve(existing, decision_id, actor, target, workspace)

            permits = (
                _PERMITS_POSTGRES
                if transaction.dialect.name == "postgresql"
                else _PERMITS_SQLITE
            )
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise OnboardingDecisionStoreUnavailable
            if transaction.execute(
                permits, {"actor": actor, "target": target, "workspace": workspace}
            ).first() is None:
                return None

            # A concurrent identical decision may have committed while this
            # transaction waited for the authority row lock.
            existing = transaction.execute(
                _SELECT_DECISION, {"decision": decision}
            ).first()
            if existing is not None:
                return self._resolve(existing, decision_id, actor, target, workspace)

            generated = self._generate_request_id()
            if type(generated) is not ProvisioningRequestId:
                raise OnboardingDecisionStoreUnavailable
            request = _encode(generated.value)
            try:
                transaction.execute(
                    _INSERT_DECISION,
                    {
                        "decision": decision,
                        "request": request,
                        "actor": actor,
                        "target": target,
                        "workspace": workspace,
                    },
                )
            except IntegrityError:
                raise OnboardingDecisionStoreUnavailable from None
            return AuthorizedOnboardingDecision(
                decision_id,
                generated,
                principal.user_id,
                target_user_id,
                target_workspace_id,
            )

    @staticmethod
    def _resolve(
        row: Row[Any],
        decision_id: OnboardingDecisionId,
        actor: bytes,
        target: bytes,
        workspace: bytes,
    ) -> AuthorizedOnboardingDecision:
        if (
            _stored(row.actor_user_id) != actor
            or _stored(row.target_user_id) != target
            or _stored(row.target_workspace_id) != workspace
        ):
            raise OnboardingDecisionConflict
        return AuthorizedOnboardingDecision(
            decision_id,
            ProvisioningRequestId(_decode(row.provisioning_request)),
            UserId(_decode(row.actor_user_id)),
            UserId(_decode(row.target_user_id)),
            WorkspaceId(_decode(row.target_workspace_id)),
        )
