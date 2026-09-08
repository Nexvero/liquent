"""Controlled offline onboarding and pending-login admission binding."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    IdentityAdmissionProvisioningConflict,
    IdentityAdmissionStoreUnavailable,
    OidcLoginTransactionStoreUnavailable,
    OnboardingDecisionConflict,
    OnboardingDecisionStoreUnavailable,
)
from liquent_platform.persistence.identity_onboarding_composition import (
    compose_identity_onboarding,
)
from liquent_platform.persistence.oidc_admission_login_binding import (
    DatabaseOidcPendingLoginAdmissionBinding,
)

_ADMISSION_LIFETIME = timedelta(minutes=10)


class OidcAdmissionLoginOperatorInputRejected(Exception):
    code = "oidc_admission_login_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class OidcAdmissionLoginOperatorRequest:
    actor_user_id: UserId = field(repr=False)
    decision_id: OnboardingDecisionId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    target_workspace_id: WorkspaceId = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise OidcAdmissionLoginOperatorInputRejected
    return value


def load_operator_request(path: Path) -> OidcAdmissionLoginOperatorRequest:
    try:
        value = json.loads(_read_private(path))
        if not isinstance(value, dict) or set(value) != {
            "actor_user_id", "decision_id", "target_user_id", "target_workspace_id"
        }:
            raise OidcAdmissionLoginOperatorInputRejected
        return OidcAdmissionLoginOperatorRequest(
            UserId(_string(value["actor_user_id"])),
            OnboardingDecisionId(_string(value["decision_id"])),
            UserId(_string(value["target_user_id"])),
            WorkspaceId(_string(value["target_workspace_id"])),
        )
    except OidcAdmissionLoginOperatorInputRejected:
        raise
    except Exception:
        raise OidcAdmissionLoginOperatorInputRejected from None


def apply_operator_request(
    engine: Engine,
    request: OidcAdmissionLoginOperatorRequest,
    *,
    material: SecureIdentityAuthorityMaterialGenerator,
    now: datetime,
) -> bool:
    clock = lambda: now
    composition = compose_identity_onboarding(
        engine,
        admission_lifetime=_ADMISSION_LIFETIME,
        now=clock,
        material=material,
    )
    admission = composition.onboarding.onboard(
        request.decision_id,
        SessionPrincipal(request.actor_user_id),
        request.target_user_id,
        request.target_workspace_id,
    )
    if admission is None:
        return False
    return DatabaseOidcPendingLoginAdmissionBinding(
        engine, now=clock
    ).bind_admission(admission)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-oidc-admission-login")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-decision-id")
    apply = commands.add_parser("apply")
    apply.add_argument("--database-url-file", required=True, type=Path)
    apply.add_argument("--request", required=True, type=Path)
    return parser


def _emit(outcome: str) -> None:
    sys.stdout.write(json.dumps({"outcome": outcome}, separators=(",", ":")) + "\n")


def _fail(code: str, exit_code: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    material = SecureIdentityAuthorityMaterialGenerator()
    if args.command == "new-decision-id":
        sys.stdout.write(material.new_onboarding_decision_id().value + "\n")
        return 0
    engine: Engine | None = None
    try:
        request = load_operator_request(args.request)
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise OidcAdmissionLoginOperatorInputRejected
        engine = build_engine(database_url)
        bound = apply_operator_request(
            engine, request, material=material, now=datetime.now(UTC)
        )
    except OidcAdmissionLoginOperatorInputRejected:
        _fail(OidcAdmissionLoginOperatorInputRejected.code, 2)
    except (OnboardingDecisionConflict, IdentityAdmissionProvisioningConflict):
        _fail("oidc_admission_login_operator_conflict", 3)
    except (
        OnboardingDecisionStoreUnavailable,
        IdentityAdmissionStoreUnavailable,
        OidcLoginTransactionStoreUnavailable,
    ):
        _fail("oidc_admission_login_operator_unavailable", 4)
    except Exception:
        _fail("oidc_admission_login_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    _emit("bound" if bound else "rejected")
    return 0 if bound else 5
