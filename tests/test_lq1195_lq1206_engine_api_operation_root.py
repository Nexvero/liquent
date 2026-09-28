import shutil
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as command
from tools.engine_api_joint_staging_operation_root import resolve_operation_root
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def operation_root(tmp_path):
    generated_parent=tmp_path/"generated";generated_parent.mkdir();generated=run_root(generated_parent);root=tmp_path/"operation";root.mkdir(mode=0o700);shutil.move(str(generated),root/"source-set");acceptance=root/"accepted-runs";acceptance.mkdir(mode=0o700);return root.resolve()

def test_operation_root_binds_exact_fixed_children(tmp_path):
    root=operation_root(tmp_path);resolved=resolve_operation_root(root);assert resolved.source_root==root/"source-set" and resolved.acceptance_root==root/"accepted-runs" and repr(resolved)=="JointEngineApiStagingOperationRoots()"

@pytest.mark.parametrize("mutation",("root-mode","extra","missing-source","source-mode","acceptance-mode","source-link"))
def test_operation_root_rejects_layout_or_private_boundary_mutation(tmp_path,mutation):
    root=operation_root(tmp_path)
    if mutation=="root-mode": root.chmod(0o750)
    elif mutation=="extra": (root/"extra").mkdir(mode=0o700)
    elif mutation=="missing-source": shutil.rmtree(root/"source-set")
    elif mutation=="source-mode": (root/"source-set").chmod(0o750)
    elif mutation=="acceptance-mode": (root/"accepted-runs").chmod(0o750)
    else:
        target=root/"source-set";moved=root/"real-source";target.rename(moved);target.symlink_to(moved,target_is_directory=True)
    with pytest.raises(ManifestHandoffRegistryUnavailable): resolve_operation_root(root)

def test_operation_acceptance_and_audits_share_bound_roots(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);command.accept_once(root);command.audit(root,accepted_source=False);command.audit(root,accepted_source=True)

def test_operation_cli_exposes_only_operation_root_and_closed_modes(tmp_path,monkeypatch):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW);prefix=["--operation-root",str(root),"--mode"]
    assert command.main(prefix+["audit-registry"])==0 and command.main(prefix+["accept-once"])==0 and command.main(prefix+["audit-accepted-source"])==0 and command.main(prefix+["unknown"])==2

def test_alternate_acceptance_root_cannot_be_supplied(tmp_path):
    root=operation_root(tmp_path);alternate=tmp_path/"alternate";alternate.mkdir(mode=0o700)
    assert command.main(["--operation-root",str(root),"--acceptance-root",str(alternate),"--mode","audit-registry"])==2
