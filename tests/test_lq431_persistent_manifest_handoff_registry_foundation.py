from datetime import datetime, timezone
import inspect
from pathlib import Path

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffAttemptView,
    ManifestHandoffName,
    ManifestHandoffObservationKind,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationId,
    ReservedManifestHandoffAttempt,
)
from liquent_platform.identity.ports import (
    AuthorizedManifestHandoffAttemptLookup,
    AuthorizedManifestHandoffAttemptReservation,
)


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "src/liquent_platform/persistence/alembic/versions/20260819_0028_manifest_handoff_attempt_registry.py"


def test_ids_names_and_views_are_closed_and_repr_safe() -> None:
    values = (
        ManifestHandoffRegistryScopeId("scope-secret"),
        ManifestHandoffAttemptId("attempt-secret"),
        ManifestHandoffReservationId("reservation-secret"),
    )
    assert all("secret" not in repr(value) for value in values)
    for invalid in ("", ".", "../bad", "bad/name", "a" * 129):
        try:
            ManifestHandoffName(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid handoff name")

    reserved_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    attempt = ReservedManifestHandoffAttempt(
        values[2], values[1], values[0], UserId("user-secret"),
        ManifestHandoffName("attempt-431"), reserved_at,
    )
    view = ManifestHandoffAttemptView(
        values[1], values[0], UserId("user-secret"),
        attempt.handoff_name, ManifestHandoffObservationKind.RESERVED, reserved_at,
    )
    assert view.latest_observation is ManifestHandoffObservationKind.RESERVED
    assert "user-secret" not in repr(view)


def test_ports_accept_no_allow_role_status_or_generated_attempt_id() -> None:
    reserve = inspect.signature(AuthorizedManifestHandoffAttemptReservation.reserve_attempt)
    lookup = inspect.signature(AuthorizedManifestHandoffAttemptLookup.get_attempt)
    assert tuple(reserve.parameters) == (
        "self", "reservation_id", "actor_user_id", "scope_id", "handoff_name"
    )
    assert tuple(lookup.parameters) == (
        "self", "actor_user_id", "scope_id", "handoff_name"
    )
    forbidden = {"allow", "role", "status", "attempt_id", "now", "authority"}
    assert forbidden.isdisjoint(reserve.parameters)
    assert forbidden.isdisjoint(lookup.parameters)


def test_migration_is_linear_empty_and_permanently_unique() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "20260819_0028"' in text
    assert 'down_revision: str | Sequence[str] | None = "20260819_0027"' in text
    assert "manifest_handoff_registry_scopes" in text
    assert "manifest_handoff_registry_authorities" in text
    assert "manifest_handoff_attempts" in text
    assert "manifest_handoff_attempt_observations" in text
    assert '"scope_id", "handoff_name", name="uq_manifest_handoff_attempt_scope_name"' in text
    assert "op.bulk_insert" not in text
    assert "INSERT" not in text


def test_observation_history_is_ordered_and_append_only_by_shape() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert '"attempt_id",\n            "sequence_number"' in text
    assert '"sequence_number>0"' in text
    for kind in ManifestHandoffObservationKind:
        assert f"'{kind.value}'" in text
    assert "ondelete=" not in text


def test_roadmap_and_contract_keep_later_work_separate() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-431 persistent manifest handoff registry foundation:" in roadmap
    assert "`docs/lq-431-persistent-manifest-handoff-registry-foundation.md`" in roadmap
    assert "nächster Slice LQ-432" in roadmap
