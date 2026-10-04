"""Private immutable inputs, workspace-bound resolution, voluntary feedback."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import Engine, text

from liquent.research_pilot.customer_data_check import check_customer_data
from liquent.research_pilot.customer_feedback import _validate
from liquent.research_pilot.execution import canonical_json, fingerprint, validate_configuration
from liquent_platform.application.customer_research import (
    PILOT_STRATEGY_VERSION, PilotBacktestExecution, customer_input_binding,
)
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.identity.research import ExperimentId, StrategyVersionId, WorkspaceId

MAX_CONFIGURATION_BYTES = 64 * 1024


def _bounded_configuration(value: str) -> str:
    if type(value) is not str or len(value.encode("utf-8")) > MAX_CONFIGURATION_BYTES:
        raise ValueError("Research-Konfiguration darf höchstens 64 KiB umfassen.")
    return value


class CustomerResearchUnavailable(Exception):
    """Fail closed without SQL, credentials, CSV rows or customer text in errors."""

    def __init__(self) -> None:
        super().__init__("customer_research_unavailable")


def _identity(value: str) -> bytes:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError("Aktive Benutzer- und Workspace-Zuordnung erforderlich.")
    return value.encode("utf-8")


def _authorized(connection, owner: bytes, workspace: bytes, permission: str) -> bool:
    return connection.execute(text(
        "SELECT 1 FROM identity_users u "
        "JOIN workspace_memberships m ON m.user_id=u.user_id "
        "JOIN identity_workspaces w ON w.workspace_id=m.workspace_id "
        "WHERE u.user_id=:owner AND m.workspace_id=:workspace "
        "AND u.status='active' AND w.status='active' AND m.status='active' "
        "AND EXISTS (SELECT 1 FROM workspace_membership_permissions p "
        "WHERE p.user_id=m.user_id AND p.workspace_id=m.workspace_id "
        "AND (p.permission=:permission OR p.permission='research:write'))"
    ), {"owner": owner, "workspace": workspace, "permission": permission}).first() is not None


class DatabaseCustomerResearchStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseCustomerResearchStore()"

    def bind_request(self, owner: str, workspace: str, raw: bytes,
                     configuration: dict, expected_binding: str,
                     data_rights: bool, execution_approved: bool) -> ExperimentSnapshot:
        owner_bytes, workspace_bytes = _identity(owner), _identity(workspace)
        if data_rights is not True or execution_approved is not True:
            raise ValueError("Datenrechte und Ausführung müssen ausdrücklich bestätigt werden.")
        config = validate_configuration(configuration)
        configuration_json = _bounded_configuration(canonical_json(config))
        readiness = check_customer_data(raw, config["dataset"]["timeframe"])
        if readiness["status"] == "blocked":
            raise ValueError("Ungültige CSV: " + readiness["meaning"])
        binding = customer_input_binding(raw, config)
        if (type(expected_binding) is not str
                or re.fullmatch(r"sha256:[0-9a-f]{64}", expected_binding) is None
                or not hmac.compare_digest(binding, expected_binding)):
            raise ValueError("Daten oder Konfiguration wurden seit der Freigabe verändert.")
        dataset_fingerprint = "sha256:" + hashlib.sha256(raw).hexdigest()
        values = {"request": secrets.token_urlsafe(32).encode("ascii"),
                  "owner": owner_bytes, "workspace": workspace_bytes,
                  "binding": binding, "dataset": dataset_fingerprint,
                  "configuration": configuration_json, "raw": raw,
                  "now": datetime.now(timezone.utc)}
        try:
            with self._engine.begin() as connection:
                if not _authorized(connection, owner_bytes, workspace_bytes, "research:write"):
                    raise ValueError("Keine aktive Research-Schreibberechtigung in diesem Workspace.")
                connection.execute(text(
                    "INSERT INTO customer_research_requests "
                    "(request_id,owner_user_id,workspace_id,input_binding,dataset_fingerprint,"
                    "configuration_json,dataset_csv,data_rights,execution_approved,created_at) "
                    "VALUES (:request,:owner,:workspace,:binding,:dataset,:configuration,:raw,TRUE,TRUE,:now) "
                    "ON CONFLICT (owner_user_id,workspace_id,input_binding) DO NOTHING"
                ), values)
                row = connection.execute(text(
                    "SELECT request_id,configuration_json,dataset_fingerprint FROM customer_research_requests "
                    "WHERE owner_user_id=:owner AND workspace_id=:workspace AND input_binding=:binding"
                ), values).mappings().one()
                if row["configuration_json"] != values["configuration"] or row["dataset_fingerprint"] != dataset_fingerprint:
                    raise CustomerResearchUnavailable
        except (ValueError, CustomerResearchUnavailable):
            raise
        except Exception:
            raise CustomerResearchUnavailable from None
        return ExperimentSnapshot(
            ExperimentId(fingerprint({"owner": owner, "workspace": workspace, "binding": binding})),
            WorkspaceId(workspace), config["order"]["title"], bytes(row["request_id"]).decode("ascii"),
            dataset_fingerprint, StrategyVersionId(PILOT_STRATEGY_VERSION),
            freeze_parameters({"configuration_json": values["configuration"], "input_binding": binding,
                               "request_owner": owner}), (), (),
        )

    def resolve(self, snapshot: ExperimentSnapshot) -> PilotBacktestExecution:
        if snapshot.strategy_version_id != PILOT_STRATEGY_VERSION:
            raise ValueError("Nicht unterstützte Research-Konfiguration.")
        parameters = dict(snapshot.strategy_parameters)
        if set(parameters) != {"configuration_json", "input_binding", "request_owner"} or snapshot.risk_parameters or snapshot.cost_parameters:
            raise ValueError("Research-Eingabebindung ist unvollständig.")
        _bounded_configuration(parameters["configuration_json"])
        owner, workspace = _identity(parameters["request_owner"]), _identity(str(snapshot.workspace_id))
        try:
            with self._engine.connect() as connection:
                if not _authorized(connection, owner, workspace, "research:write"):
                    raise ValueError("Research-Ausführungsberechtigung nicht mehr aktiv.")
                row = connection.execute(text(
                    "SELECT * FROM customer_research_requests WHERE request_id=:request "
                    "AND owner_user_id=:owner AND workspace_id=:workspace"
                ), {"request": _identity(snapshot.dataset_ref), "owner": owner,
                    "workspace": workspace}).mappings().one_or_none()
        except ValueError:
            raise
        except Exception:
            raise CustomerResearchUnavailable from None
        if row is None:
            raise ValueError("Research-Eingaben sind für diesen Workspace nicht verfügbar.")
        raw = bytes(row["dataset_csv"])
        config = validate_configuration(json.loads(_bounded_configuration(row["configuration_json"])))
        binding = customer_input_binding(raw, config)
        expected_id = fingerprint({"owner": parameters["request_owner"],
                                   "workspace": str(snapshot.workspace_id), "binding": binding})
        if (not row["data_rights"] or not row["execution_approved"]
                or binding != row["input_binding"] or binding != parameters["input_binding"]
                or row["configuration_json"] != parameters["configuration_json"]
                or row["dataset_fingerprint"] != snapshot.dataset_fingerprint
                or "sha256:" + hashlib.sha256(raw).hexdigest() != snapshot.dataset_fingerprint
                or expected_id != snapshot.experiment_id or config["order"]["title"] != snapshot.title):
            raise ValueError("Gespeicherte Research-Eingaben stimmen nicht mit der Freigabe überein.")
        return PilotBacktestExecution(raw, config, str(snapshot.experiment_id))

    def save_feedback(self, owner: str, workspace: str, value: dict,
                      synthetic: bool) -> None:
        owner_bytes, workspace_bytes = _identity(owner), _identity(workspace)
        if type(synthetic) is not bool:
            raise ValueError("Synthetische Rückmeldungen müssen ausdrücklich gekennzeichnet sein.")
        payload = canonical_json(_validate(value))
        try:
            with self._engine.begin() as connection:
                if not _authorized(connection, owner_bytes, workspace_bytes, "research:read"):
                    raise ValueError("Keine aktive Research-Berechtigung in diesem Workspace.")
                connection.execute(text(
                    "INSERT INTO customer_research_feedback "
                    "(feedback_id,owner_user_id,workspace_id,synthetic,feedback_json,evidence_type,created_at) "
                    "VALUES (:id,:owner,:workspace,:synthetic,:payload,'self_report_not_purchase',:now)"
                ), {"id": secrets.token_urlsafe(32).encode("ascii"), "owner": owner_bytes,
                    "workspace": workspace_bytes, "synthetic": synthetic, "payload": payload,
                    "now": datetime.now(timezone.utc)})
        except ValueError:
            raise
        except Exception:
            raise CustomerResearchUnavailable from None
