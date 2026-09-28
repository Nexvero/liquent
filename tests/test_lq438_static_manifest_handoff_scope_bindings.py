from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_scope_bindings import (
    StaticManifestHandoffScopeBindings,
)
from liquent_platform.identity.ports import ManifestHandoffScopeBindingLookup


def _binding(scope: str, source: str, target: str) -> ManifestHandoffScopeBinding:
    return ManifestHandoffScopeBinding(
        ManifestHandoffRegistryScopeId(scope), Path(source), Path(target)
    )


def test_resolves_only_the_exact_explicit_scope() -> None:
    first = _binding("scope-438-a", "/controlled/a", "/private/a")
    second = _binding("scope-438-b", "/controlled/b", "/private/b")
    resolver = StaticManifestHandoffScopeBindings((first, second))

    assert resolver.get_binding(first.scope_id) is first
    assert resolver.get_binding(second.scope_id) is second
    assert resolver.get_binding(ManifestHandoffRegistryScopeId("absent")) is None
    assert resolver.get_binding("") is None  # type: ignore[arg-type]
    lookup: ManifestHandoffScopeBindingLookup = resolver
    assert lookup.get_binding(first.scope_id) is first


def test_copies_one_shot_configuration_without_discovery_or_mutation() -> None:
    binding = _binding("scope-438", "/controlled/source", "/private/target")
    supplied = iter((binding,))
    resolver = StaticManifestHandoffScopeBindings(supplied)

    assert resolver.get_binding(binding.scope_id) is binding
    assert tuple(resolver.__slots__) == ("__bindings",)
    assert not hasattr(resolver, "add_binding")
    assert not hasattr(resolver, "remove_binding")
    assert "/controlled/source" not in repr(resolver)
    assert "/private/target" not in repr(resolver)


@pytest.mark.parametrize(
    "bindings",
    (
        (
            _binding("same", "/controlled/a", "/private/a"),
            _binding("same", "/controlled/b", "/private/b"),
        ),
        (
            _binding("a", "/controlled/a", "/private/shared"),
            _binding("b", "/controlled/b", "/private/shared"),
        ),
        (
            _binding("a", "/controlled/a", "/private/root"),
            _binding("b", "/controlled/b", "/private/root/nested"),
        ),
        (
            _binding("a", "/controlled/a", "/private/a"),
            _binding("b", "/private/a/source", "/private/b"),
        ),
    ),
)
def test_rejects_ambiguous_scope_or_cross_scope_roots(
    bindings: tuple[ManifestHandoffScopeBinding, ...],
) -> None:
    with pytest.raises(ValueError):
        StaticManifestHandoffScopeBindings(bindings)


def test_allows_a_shared_controlled_source_with_distinct_private_targets() -> None:
    first = _binding("a", "/controlled/shared", "/private/a")
    second = _binding("b", "/controlled/shared", "/private/b")

    resolver = StaticManifestHandoffScopeBindings((first, second))

    assert resolver.get_binding(first.scope_id) is first
    assert resolver.get_binding(second.scope_id) is second


def test_roadmap_records_static_resolver_and_next_slice() -> None:
    root = Path(__file__).parents[1]
    roadmap = (root / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-438 static manifest handoff scope-binding resolver:" in roadmap
    assert "`docs/lq-438-static-manifest-handoff-scope-binding-resolver.md`" in roadmap
    assert "nächster Slice LQ-439" in roadmap
