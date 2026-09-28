from dataclasses import replace
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_operation_verify as operation_subject
from tools.engine_api_joint_staging_operation_root import resolve_operation_root, validate_operation_roots


def _changed(value,index,replacement):
    items=list(value);items[index]=replacement;return tuple(items)


def test_operation_resolution_carries_three_descriptor_states(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root)
    assert resolved.root_state[:2]==resolved.root_identity
    assert resolved.source_state[:2]==resolved.source_identity
    assert resolved.acceptance_state[:2]==resolved.acceptance_identity


@pytest.mark.parametrize("field,identity", (("root_state","source_identity"),("source_state","acceptance_identity"),("acceptance_state","root_identity")))
def test_operation_roots_reject_state_identity_mismatch(tmp_path,field,identity):
    resolved=resolve_operation_root(operation_root(tmp_path));state=getattr(resolved,field);other=getattr(resolved,identity)
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,**{field:(*other,*state[2:])})


@pytest.mark.parametrize("field,index,replacement", (("root_state",2,stat.S_IFREG|0o700),("source_state",2,stat.S_IFDIR|0o755),("acceptance_state",3,99999999)))
def test_operation_roots_reject_invalid_state_semantics(tmp_path,field,index,replacement):
    resolved=resolve_operation_root(operation_root(tmp_path));state=_changed(getattr(resolved,field),index,replacement)
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(resolved,**{field:state})


def test_final_validation_rejects_same_inode_child_metadata_change(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root);child=root/"source-set";child.chmod(0o755);child.chmod(0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable): validate_operation_roots(root,resolved)


def test_operation_wrapper_rejects_transient_child_metadata_change(tmp_path):
    root=operation_root(tmp_path);child=root/"accepted-runs"
    def changing(resolved): child.chmod(0o755);child.chmod(0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable): operation_subject._within_operation_roots(root,changing)


def test_unchanged_operation_state_remains_valid(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root);assert replace(resolved)==resolved;validate_operation_roots(root,resolved)
