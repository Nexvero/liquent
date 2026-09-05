"""Controlled terminal handoff to PostgreSQL volume-deletion finalization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import (
    _evidence_root, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_volume_deletion import (
    DisposablePostgresVolumeDeletionUnavailable, _binding as _deletion_binding,
    _claim as _deletion_claim, _historical_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_continue import (
    DisposablePostgresVolumeDeletionContinueUnavailable,
    _authorization as _continuation_authorization, _binding as _continuation_binding,
    _claim as _continuation_claim,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_continue_finalize import (
    KEYS as CONTINUATION_FINALIZATION_KEYS,
    DisposablePostgresVolumeDeletionContinueFinalizeUnavailable,
    _authorization as _continuation_finalization_authorization,
    _binding as _continuation_finalization_binding,
    _existing as _continuation_finalization_evidence,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_finalize import (
    DisposablePostgresVolumeDeletionFinalizeUnavailable,
    _authorization as _terminal_finalization_authorization,
    _binding as _terminal_finalization_binding,
    _existing as _terminal_finalization_evidence,
    finalize_disposable_postgres_volume_deletion,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_reconcile import (
    DisposablePostgresVolumeDeletionReconcileUnavailable,
    _authorization as _terminal_reconciliation_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    _current, _json, _opaque,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)


KEYS = (
    CONTINUATION_FINALIZATION_KEYS
    - {"operation", "executor_id", "authorizer_id", "reviewer_id",
       "valid_from", "valid_until"}
    | {"volume_deletion_terminal_handoff_id",
       "terminal_volume_deletion_reconciliation_id",
       "terminal_volume_deletion_finalization_id",
       "volume_deletion_continuation_finalization_authorization_sha256",
       "volume_deletion_continuation_finalization_evidence_sha256",
       "terminal_volume_deletion_reconciliation_authorization_sha256",
       "terminal_volume_deletion_finalization_authorization_sha256",
       "operation", "executor_id", "authorizer_id", "reviewer_id",
       "valid_from", "valid_until"}
)
POSITIVE = {
    "continuation_evidence_confirmed",
    "volume_removal_ready_for_deletion_finalization",
}


class DisposablePostgresVolumeDeletionTerminalHandoffUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_terminal_handoff_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        _, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"]
            != "handoff_disposable_postgres_volume_deletion_finalization"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        for key in (
            "volume_deletion_terminal_handoff_id",
            "terminal_volume_deletion_reconciliation_id",
            "terminal_volume_deletion_finalization_id",
            "volume_deletion_continuation_finalization_id",
            "volume_deletion_continuation_reconciliation_id",
            "volume_deletion_continuation_id",
            "volume_deletion_continuation_claim_id", "volume_deletion_id",
            "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "executor_id", "authorizer_id", "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        for key in (
            "compose_sha256", "volume_deletion_authorization_sha256",
            "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
            "retention_decision_sha256", "legal_hold_decision_sha256",
            "recovery_decision_sha256",
            "volume_deletion_reconciliation_authorization_sha256",
            "volume_deletion_finalization_authorization_sha256",
            "volume_deletion_continuation_authorization_sha256",
            "volume_deletion_continuation_reconciliation_authorization_sha256",
            "volume_deletion_continuation_finalization_authorization_sha256",
            "volume_deletion_continuation_finalization_evidence_sha256",
            "terminal_volume_deletion_reconciliation_authorization_sha256",
            "terminal_volume_deletion_finalization_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        _current(value, clock=clock)
        return value
    except DisposablePostgresVolumeDeletionTerminalHandoffUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable from None


def _historical_continuation_finalization(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked = _continuation_finalization_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        return raw, checked
    except Exception:
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable from None


def _historical_continuation(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked_raw, checked = _continuation_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        if checked_raw != raw:
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        return raw, checked
    except DisposablePostgresVolumeDeletionTerminalHandoffUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_terminal_handoff",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def handoff_disposable_postgres_volume_deletion_finalization(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, terminal_volume_deletion_reconciliation_file: Path,
    terminal_volume_deletion_finalization_file: Path,
    volume_deletion_continuation_file: Path,
    volume_deletion_continuation_finalization_file: Path,
    volume_deletion_terminal_handoff_file: Path, lineage_manifest_file: Path,
    retention_decision_file: Path, legal_hold_decision_file: Path,
    recovery_decision_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        deletion_raw, deletion = _historical_authorization(volume_deletion_file)
        continuation_raw, continuation = _historical_continuation(
            volume_deletion_continuation_file,
        )
        continuation_finalization_raw, previous = _historical_continuation_finalization(
            volume_deletion_continuation_finalization_file,
        )
        terminal_reconciliation_raw, terminal_reconciliation = _json(
            terminal_volume_deletion_reconciliation_file, 32_768,
        )
        terminal_reconciliation = _terminal_reconciliation_authorization(
            terminal_volume_deletion_reconciliation_file, clock=clock,
        )
        terminal_finalization_raw, _ = _json(
            terminal_volume_deletion_finalization_file, 32_768,
        )
        terminal_finalization = _terminal_finalization_authorization(
            terminal_volume_deletion_finalization_file, clock=clock,
        )
        current = _authorization(volume_deletion_terminal_handoff_file, clock=clock)
        if (
            project_name != f"liquent-{current['run_id']}"
            or current["retained_volume"] != f"{project_name}-postgres-data"
            or current["volume_deletion_continuation_finalization_authorization_sha256"]
            != hashlib.sha256(continuation_finalization_raw).hexdigest()
            or current["terminal_volume_deletion_reconciliation_authorization_sha256"]
            != hashlib.sha256(terminal_reconciliation_raw).hexdigest()
            or current["terminal_volume_deletion_finalization_authorization_sha256"]
            != hashlib.sha256(terminal_finalization_raw).hexdigest()
            or current["terminal_volume_deletion_reconciliation_id"]
            != terminal_reconciliation["volume_deletion_reconciliation_id"]
            or current["terminal_volume_deletion_finalization_id"]
            != terminal_finalization["volume_deletion_finalization_id"]
            or terminal_finalization["volume_deletion_reconciliation_authorization_sha256"]
            != hashlib.sha256(terminal_reconciliation_raw).hexdigest()
            or any(current[key] != previous[key] for key in (
                CONTINUATION_FINALIZATION_KEYS - {
                    "schema_version", "operation", "executor_id", "authorizer_id",
                    "reviewer_id", "valid_from", "valid_until",
                }
            ))
            or len({
                current["executor_id"], current["authorizer_id"], current["reviewer_id"],
                terminal_reconciliation["executor_id"],
                terminal_reconciliation["authorizer_id"],
                terminal_reconciliation["reviewer_id"],
                terminal_finalization["executor_id"],
                terminal_finalization["authorizer_id"],
                terminal_finalization["reviewer_id"],
            }) != 9
        ):
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        continuation_finalization_binding = _continuation_finalization_binding(
            previous, volume_deletion_continuation_finalization_file,
        )
        continuation_finalization_stem = hashlib.sha256(
            current["volume_deletion_continuation_finalization_id"].encode(),
        ).hexdigest()
        continuation_finalization_evidence = evidence_directory / (
            "postgres-volume-deletion-continuation-finalization-"
            f"{continuation_finalization_stem}.json"
        )
        outcome = _continuation_finalization_evidence(
            continuation_finalization_evidence, continuation_finalization_binding,
        )
        if outcome not in POSITIVE:
            return _result("investigation_required")
        if current["volume_deletion_continuation_finalization_evidence_sha256"] != hashlib.sha256(
            continuation_finalization_evidence.read_bytes(),
        ).hexdigest():
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        continuation_binding = _continuation_binding(continuation, continuation_raw)
        continuation_claim_stem = hashlib.sha256(
            current["volume_deletion_continuation_claim_id"].encode(),
        ).hexdigest()
        continuation_claim = evidence_directory / (
            f".postgres-volume-deletion-continuation-{continuation_claim_stem}.claim"
        )
        if continuation_claim.exists():
            if not _continuation_claim(continuation_claim, continuation_binding):
                raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
            return _result("investigation_required")
        deletion_binding = _deletion_binding(deletion, deletion_raw)
        original_claim_stem = hashlib.sha256(
            current["volume_deletion_claim_id"].encode(),
        ).hexdigest()
        original_claim = evidence_directory / f".postgres-volume-deletion-{original_claim_stem}.claim"
        terminal_binding = _terminal_finalization_binding(
            terminal_finalization, terminal_volume_deletion_finalization_file,
        )
        terminal_stem = hashlib.sha256(
            terminal_finalization["volume_deletion_finalization_id"].encode(),
        ).hexdigest()
        terminal_evidence = evidence_directory / (
            f"postgres-volume-deletion-finalization-{terminal_stem}.json"
        )
        existing = _terminal_finalization_evidence(terminal_evidence, terminal_binding)
        if existing is None:
            if not original_claim.exists():
                return _result("investigation_required")
            if not _deletion_claim(original_claim, deletion_binding):
                raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        root_descriptor = _evidence_root(evidence_directory)
        raw = finalize_disposable_postgres_volume_deletion(
            docker_executable=docker_executable,
            volume_disposition_file=volume_disposition_file,
            volume_deletion_file=volume_deletion_file,
            volume_deletion_reconciliation_file=
                terminal_volume_deletion_reconciliation_file,
            volume_deletion_finalization_file=terminal_volume_deletion_finalization_file,
            lineage_manifest_file=lineage_manifest_file,
            retention_decision_file=retention_decision_file,
            legal_hold_decision_file=legal_hold_decision_file,
            recovery_decision_file=recovery_decision_file,
            project_name=project_name, evidence_directory=evidence_directory,
            processes=processes, clock=clock,
        )
        result = json.loads(raw, object_pairs_hook=_pairs)
        if (
            type(result) is not dict
            or set(result) != {"schema_version", "operation", "outcome"}
            or result["schema_version"] != 1
            or result["operation"] != "disposable_postgres_volume_deletion_finalization"
            or result["outcome"] not in {
                "not_found", "volume_removal_finalized", "deletion_evidence_confirmed",
                "continuation_required", "investigation_required",
            }
        ):
            raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable
        if result["outcome"] in {"volume_removal_finalized", "deletion_evidence_confirmed"}:
            return _result("volume_deletion_finalized")
        return _result("investigation_required")
    except DisposablePostgresVolumeDeletionTerminalHandoffUnavailable:
        raise
    except (
        DisposablePostgresVolumeDeletionUnavailable,
        DisposablePostgresVolumeDeletionContinueUnavailable,
        DisposablePostgresVolumeDeletionContinueFinalizeUnavailable,
        DisposablePostgresVolumeDeletionFinalizeUnavailable,
        DisposablePostgresVolumeDeletionReconcileUnavailable,
    ):
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionTerminalHandoffUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-delete-terminal-handoff",
        add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "terminal-volume-deletion-reconciliation-file",
        "terminal-volume-deletion-finalization-file",
        "volume-deletion-continuation-file",
        "volume-deletion-continuation-finalization-file",
        "volume-deletion-terminal-handoff-file", "lineage-manifest-file",
        "retention-decision-file", "legal-hold-decision-file",
        "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(handoff_disposable_postgres_volume_deletion_finalization(
            **vars(parser.parse_args(argv)),
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
