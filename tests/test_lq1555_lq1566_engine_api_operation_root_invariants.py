from dataclasses import replace
from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools.engine_api_joint_staging_operation_root import resolve_operation_root, validate_operation_roots


@pytest.mark.parametrize("field,value", (("source_root",Path("source-set")),("acceptance_root",Path("accepted-runs")),("source_root",Path("/")),("acceptance_root",Path("/"))))
def test_operation_roots_reject_non_absolute_or_broad_paths(tmp_path,field,value):
    resolved=resolve_operation_root(operation_root(tmp_path))
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,**{field:value})


@pytest.mark.parametrize("field,name", (("source_root","sources"),("acceptance_root","registry")))
def test_operation_roots_require_exact_child_names(tmp_path,field,name):
    resolved=resolve_operation_root(operation_root(tmp_path));value=resolved.source_root.parent/name
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,**{field:value})


def test_operation_roots_require_one_shared_parent(tmp_path):
    resolved=resolve_operation_root(operation_root(tmp_path));other=(tmp_path/"other"/"accepted-runs").resolve()
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,acceptance_root=other)


@pytest.mark.parametrize("field,source", (("source_identity","root_identity"),("acceptance_identity","root_identity"),("acceptance_identity","source_identity")))
def test_operation_roots_require_three_distinct_identities(tmp_path,field,source):
    resolved=resolve_operation_root(operation_root(tmp_path))
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,**{field:getattr(resolved,source)})


def test_authentic_operation_roots_satisfy_closed_invariants(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root);assert replace(resolved)==resolved;validate_operation_roots(root,resolved)
