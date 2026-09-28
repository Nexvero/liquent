from pathlib import Path
import inspect

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffCompositionConflict,
    ManifestHandoffCompositionKind,
    ManifestHandoffCompositionRequest,
    ManifestHandoffCompositionResult,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.ports import (
    ControlledManifestHandoffComposition,
    ManifestHandoffScopeBindingLookup,
)


SCOPE = ManifestHandoffRegistryScopeId("scope-437")
ATTEMPT = ManifestHandoffAttemptId("attempt-437")
FACTS = ManifestHandoffFacts("c" * 64, 4)


def test_scope_binding_requires_absolute_lexically_separate_roots() -> None:
    binding = ManifestHandoffScopeBinding(
        SCOPE, Path("/controlled/source"), Path("/private/handoff")
    )
    assert "controlled/source" not in repr(binding)
    assert "private/handoff" not in repr(binding)
    for source, target in (
        (Path("relative"), Path("/target")),
        (Path("/same"), Path("/same")),
        (Path("/root"), Path("/root/inside")),
        (Path("/root/inside"), Path("/root")),
        (Path("/source/../other"), Path("/target")),
    ):
        with pytest.raises(ValueError):
            ManifestHandoffScopeBinding(SCOPE, source, target)


def test_request_contains_no_paths_outcomes_or_observation_ids() -> None:
    request = ManifestHandoffCompositionRequest(
        ManifestHandoffReservationId("reservation-437"),
        UserId("actor-437"),
        SCOPE,
        ManifestHandoffName("handoff-437"),
    )
    assert "actor-437" not in repr(request)
    fields = set(request.__dataclass_fields__)
    assert fields == {"reservation_id", "actor_user_id", "scope_id", "handoff_name"}
    assert not fields & {"source_root", "target_root", "outcome", "observation_id", "allow"}


def test_confirmed_and_reconciliation_results_are_closed() -> None:
    confirmed = ManifestHandoffCompositionResult(
        ATTEMPT,
        ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF,
        "handoff-437.json",
        FACTS,
    )
    assert confirmed.staging_authorized is False
    assert confirmed.commit_authorized is False
    assert "attempt-437" not in repr(confirmed)
    assert "c" * 64 not in repr(confirmed)
    pending = ManifestHandoffCompositionResult(
        ATTEMPT, ManifestHandoffCompositionKind.RECONCILIATION_REQUIRED
    )
    assert pending.filename is None and pending.facts is None
    for kind, filename, facts in (
        (ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF, None, FACTS),
        (ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF, "../bad.json", FACTS),
        (ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF, "bad\\name.json", FACTS),
        (ManifestHandoffCompositionKind.RECONCILIATION_REQUIRED, "bad.json", FACTS),
    ):
        with pytest.raises(ValueError):
            ManifestHandoffCompositionResult(ATTEMPT, kind, filename, facts)


def test_conflict_and_ports_are_minimal() -> None:
    assert repr(ManifestHandoffCompositionConflict()) == "ManifestHandoffCompositionConflict()"
    binding = inspect.signature(ManifestHandoffScopeBindingLookup.get_binding)
    composition = inspect.signature(ControlledManifestHandoffComposition.handoff)
    assert tuple(binding.parameters) == ("self", "scope_id")
    assert tuple(composition.parameters) == ("self", "request")


def test_roadmap_links_types_and_ports_without_implementation() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-437 manifest handoff composition types and closed ports:" in roadmap
    assert "`docs/lq-437-manifest-handoff-composition-types-and-closed-ports.md`" in roadmap
    assert "nächster Slice LQ-438" in roadmap
