import shutil
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as command
from tools.engine_api_joint_staging_operation_root import resolve_operation_root,validate_operation_roots
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def test_operation_resolution_captures_three_distinct_identities(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root);assert len({resolved.root_identity,resolved.source_identity,resolved.acceptance_identity})==3;validate_operation_roots(root,resolved)

@pytest.mark.parametrize("target",("root","source","acceptance"))
def test_identity_validation_rejects_replaced_directory(tmp_path,target):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root)
    if target=="root": moved=tmp_path/"old-operation";root.rename(moved);root.mkdir(mode=0o700);shutil.copytree(moved/"source-set",root/"source-set");(root/"accepted-runs").mkdir(mode=0o700)
    else:
        path=root/("source-set" if target=="source" else "accepted-runs");moved=root/("old-source" if target=="source" else "old-acceptance");path.rename(moved)
        if target=="source": shutil.copytree(moved,path)
        else: path.mkdir(mode=0o700)
    with pytest.raises(ManifestHandoffRegistryUnavailable): validate_operation_roots(root,resolved)

def test_acceptance_revalidates_identity_after_success(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);original=command.verify_and_accept
    def swapped(source,acceptance,**kwargs):
        original(source,acceptance,**kwargs);moved=root/"old-acceptance";acceptance.rename(moved);acceptance.mkdir(mode=0o700)
    monkeypatch.setattr(command,"verify_and_accept",swapped)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.accept_once(root)

def test_registry_audit_revalidates_identity_after_success(tmp_path,monkeypatch):
    root=operation_root(tmp_path);original=command.inspect_registry
    def swapped(acceptance,**kwargs):
        result=original(acceptance,**kwargs);moved=root/"old-acceptance";acceptance.rename(moved);acceptance.mkdir(mode=0o700);return result
    monkeypatch.setattr(command,"inspect_registry",swapped)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.audit(root,accepted_source=False)

def test_unchanged_operation_identity_allows_full_lifecycle(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);command.accept_once(root);command.audit(root,accepted_source=False);command.audit(root,accepted_source=True)
