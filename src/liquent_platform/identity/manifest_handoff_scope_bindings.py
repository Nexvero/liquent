"""Explicit immutable configuration for private manifest handoff scopes."""

from collections.abc import Iterable
from pathlib import Path

from .manifest_handoff import (
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)


class StaticManifestHandoffScopeBindings:
    """Resolve only bindings supplied explicitly at construction time."""

    __slots__ = ("__bindings",)

    def __init__(self, bindings: Iterable[ManifestHandoffScopeBinding]) -> None:
        configured: dict[
            ManifestHandoffRegistryScopeId, ManifestHandoffScopeBinding
        ] = {}
        accepted: list[ManifestHandoffScopeBinding] = []
        for binding in bindings:
            if type(binding) is not ManifestHandoffScopeBinding:
                raise ValueError("manifest handoff scope binding is invalid")
            if binding.scope_id in configured:
                raise ValueError("manifest handoff scope binding is ambiguous")
            for existing in accepted:
                if _overlaps(binding.target_root, existing.target_root) or _overlaps(
                    binding.target_root, existing.source_root
                ) or _overlaps(existing.target_root, binding.source_root):
                    raise ValueError("manifest handoff scope roots are ambiguous")
            configured[binding.scope_id] = binding
            accepted.append(binding)
        self.__bindings = configured

    def get_binding(
        self, scope_id: ManifestHandoffRegistryScopeId
    ) -> ManifestHandoffScopeBinding | None:
        if type(scope_id) is not ManifestHandoffRegistryScopeId or not scope_id.value:
            return None
        return self.__bindings.get(scope_id)


def _overlaps(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        try:
            right.relative_to(left)
            return True
        except ValueError:
            return False
