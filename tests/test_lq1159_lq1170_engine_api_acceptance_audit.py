import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,inspect_staging_run_acceptance_registry,record_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools import engine_api_joint_staging_acceptance_audit as command
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def accept(source,root):
    snapshot=load_run_bound_source_set(source);record_staging_run_acceptance(root,build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority),snapshot.run_envelope))

def test_registry_inventory_is_empty_or_canonical(tmp_path):
    source,root=roots(tmp_path);assert inspect_staging_run_acceptance_registry(root)==();accept(source,root);values=inspect_staging_run_acceptance_registry(root);assert len(values)==1 and values[0].run_id.endswith("9abc")

@pytest.mark.parametrize("mutation",("unknown","mode","content","link","root-mode"))
def test_registry_inventory_rejects_every_unknown_or_unsafe_entry(tmp_path,mutation):
    source,root=roots(tmp_path);accept(source,root);marker=next(root.iterdir())
    if mutation=="unknown": path=root/"unknown";path.write_bytes(b"x");path.chmod(0o600)
    elif mutation=="mode": marker.chmod(0o640)
    elif mutation=="content": marker.write_bytes(b"invalid\n")
    elif mutation=="link": (tmp_path/"linked").hardlink_to(marker)
    else: root.chmod(0o750)
    with pytest.raises(ManifestHandoffRegistryUnavailable): inspect_staging_run_acceptance_registry(root)

def test_accepted_source_reconciliation_is_read_only(tmp_path,monkeypatch):
    source,root=roots(tmp_path);accept(source,root);before=next(root.iterdir()).read_bytes();monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_accepted_current(source,root);assert next(root.iterdir()).read_bytes()==before

@pytest.mark.parametrize("mutation",("absent","source","marker"))
def test_accepted_source_reconciliation_fails_closed(tmp_path,monkeypatch,mutation):
    source,root=roots(tmp_path)
    if mutation!="absent": accept(source,root)
    if mutation=="source": (source/"run-signature").write_bytes(b"invalid\n")
    elif mutation=="marker": next(root.iterdir()).write_bytes(b"invalid\n")
    monkeypatch.setattr(command,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_accepted_current(source,root)

def test_audit_cli_supports_registry_and_bound_source_modes(tmp_path,monkeypatch):
    source,root=roots(tmp_path);assert command.main(["--acceptance-root",str(root)])==0;accept(source,root);monkeypatch.setattr(command,"_utc_now",lambda:NOW);assert command.main(["--acceptance-root",str(root),"--source-root",str(source)])==0
