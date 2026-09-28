from dataclasses import replace
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_trust import write_manifest_handoff_supervisor_engine_api_provenance_receipt
from tools import engine_api_joint_staging_provenance_snapshot as subject
from tools.engine_api_joint_staging_receipt_verify import verify
from tests.test_lq1039_lq1050_engine_api_staging_receipt import materials,NOW

def test_snapshot_reads_each_private_source_exactly_once(tmp_path,monkeypatch):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt";write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt)
    calls=[];original=subject._read
    def observed(path,maximum): calls.append(path);return original(path,maximum)
    monkeypatch.setattr(subject,"_read",observed);snapshot=subject.load_snapshot(trust,signature,evidence,receipt_file.resolve(),*artifacts)
    assert len(calls)==9 and len(set(calls))==9 and repr(snapshot)=="JointEngineApiStagingProvenanceSnapshot()"

@pytest.mark.parametrize("index",range(9))
def test_snapshot_loader_rejects_aliases(tmp_path,index):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt"
    write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt);paths=[trust,signature,evidence,receipt_file.resolve(),*artifacts];paths[index]=paths[(index+1)%9]
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.load_snapshot(*paths)

@pytest.mark.parametrize("field",("trust","signature","evidence","receipt","artifacts"))
def test_pure_snapshot_verifier_rejects_mutated_bytes(tmp_path,field):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt"
    write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt);snapshot=subject.load_snapshot(trust,signature,evidence,receipt_file.resolve(),*artifacts)
    if field=="artifacts": mutated=replace(snapshot,artifacts=(b"wrong",*snapshot.artifacts[1:]))
    else: mutated=replace(snapshot,**{field:getattr(snapshot,field)+b"x"})
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.verify_snapshot(mutated,maximum_age_seconds=3600,now=NOW)

def test_end_to_end_verifier_uses_single_snapshot(tmp_path):
    trust,signature,evidence,artifacts,_,_,_,receipt=materials(tmp_path);receipt_file=tmp_path/"receipt"
    write_manifest_handoff_supervisor_engine_api_provenance_receipt(receipt_file.resolve(),receipt);verify(trust,signature,evidence,receipt_file.resolve(),*artifacts,maximum_age_seconds=3600,now=NOW)
