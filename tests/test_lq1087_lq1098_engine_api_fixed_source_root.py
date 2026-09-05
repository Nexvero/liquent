import shutil
from pathlib import Path
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_root_verify as command
from tools.engine_api_joint_staging_source_set import load_source_set,_SOURCES
from tests.test_lq1063_lq1074_engine_api_staging_policy import setup
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def source_root(tmp_path):
    inputs_root=tmp_path/"inputs";inputs_root.mkdir();inputs=setup(inputs_root);paths=(*inputs[:5],*inputs[5]);root=tmp_path/"source-set";root.mkdir(mode=0o700)
    for name,path in zip(_SOURCES,paths): target=root/name;shutil.copyfile(path,target);target.chmod(0o600)
    return root.resolve()

def test_fixed_source_set_loads_all_bytes_from_private_root(tmp_path):
    root=source_root(tmp_path);snapshot=load_source_set(root)
    assert snapshot.provenance.evidence==(root/"evidence").read_bytes() and repr(snapshot)=="JointEngineApiPolicyBoundProvenanceSnapshot()"

@pytest.mark.parametrize("mutation",("root-mode","extra","missing","child-mode","child-link","root-symlink"))
def test_source_root_rejects_layout_or_private_boundary_mutation(tmp_path,mutation):
    root=source_root(tmp_path)
    if mutation=="root-mode": root.chmod(0o750)
    elif mutation=="extra": extra=root/"extra";extra.write_bytes(b"x");extra.chmod(0o600)
    elif mutation=="missing": (root/"health").unlink()
    elif mutation=="child-mode": (root/"health").chmod(0o640)
    elif mutation=="child-link": (tmp_path/"health-link").hardlink_to(root/"health")
    else:
        alias=tmp_path/"alias";alias.symlink_to(root,target_is_directory=True);root=alias.absolute()
    with pytest.raises(ManifestHandoffRegistryUnavailable): load_source_set(root)

def test_root_verifier_uses_internal_current_time(tmp_path,monkeypatch):
    root=source_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_current(root)

@pytest.mark.parametrize("argv",((),("--source-root",),("--unknown","x")))
def test_root_cli_rejects_incomplete_or_unknown_arguments(argv):
    assert command.main(list(argv))==2

def test_root_cli_accepts_only_complete_fixed_root(tmp_path,monkeypatch):
    root=source_root(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);assert command.main(["--source-root",str(root)])==0
