import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue as generation
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize as final
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq345_disposable_postgres_cleanup_continuation import _processes
from tests.test_lq375_disposable_postgres_cleanup_generation_two_finalization import prepare
def setup(tmp_path:Path,state):
    values,cleanup,_=prepare(tmp_path);original=final.reconcile_disposable_postgres_cleanup_generation_continuation;final.reconcile_disposable_postgres_cleanup_generation_continuation=lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_generation_continuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    try:final.finalize_disposable_postgres_cleanup_generation_continuation(**values)
    finally:final.reconcile_disposable_postgres_cleanup_generation_continuation=original
    first=(values["predecessor_generation_continuation_file"],values["predecessor_generation_finalization_file"]);second=(values["generation_continuation_file"],values["generation_finalization_file"]);previous=json.loads(second[0].read_text());last=json.loads(second[1].read_text());stem=hashlib.sha256(last["generation_finalization_id"].encode()).hexdigest();evidence=values["evidence_directory"]/f"postgres-cleanup-generation-continuation-finalization-{stem}.json";effective=previous["resume_from"] if state=="generation_continuation_not_started" else "application_network_removed";auth={"schema_version":1,"generation_continuation_id":"generation-continuation-378","generation":3,"predecessor_kind":"repeatable_generation","predecessor_generation":2,**{k:last[k] for k in generation.ROOT},"predecessor_resume_from":previous["resume_from"],"predecessor_finalization_authorization_sha256":hashlib.sha256(second[1].read_bytes()).hexdigest(),"predecessor_finalization_evidence_sha256":hashlib.sha256(evidence.read_bytes()).hexdigest(),"operation":"continue_disposable_postgres_cleanup_from_generation","scope":"runtime_only","resume_from":effective,"executor_id":"generation-three-executor","authorizer_id":"generation-three-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["generation_continuation_file"]=_private(tmp_path/"generation-three.json",auth);values.pop("generation_reconciliation_file");values.pop("generation_finalization_file");values["predecessor_generation_continuation_file"]=None;values["predecessor_generation_finalization_file"]=None;values["generation_lineage_continuation_files"]=[first[0],second[0]];values["generation_lineage_finalization_files"]=[first[1],second[1]];values["processes"]=_processes(effective);values["clock"]=lambda:NOW;return values,cleanup,effective,first,auth
def observed(monkeypatch,state):monkeypatch.setattr(generation,"reconcile_disposable_postgres_cleanup",lambda **_:(json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode())
@pytest.mark.parametrize("state,effective",[("generation_continuation_not_started","container_removed"),("application_network_removed","application_network_removed")])
def test_generation_three_validates_complete_lineage_and_minimal_budget(tmp_path,monkeypatch,state,effective):
    values,cleanup,derived,_,_=setup(tmp_path,state);observed(monkeypatch,effective);assert derived==effective and json.loads(generation.continue_disposable_postgres_cleanup_generation(**values))["outcome"]=="runtime_removed_pending_cleanup_finalization" and cleanup.exists();commands=[c[0][1:3] for c in values["processes"].calls];expected=[]
    if effective=="container_removed":expected += [("network","rm"),("network","ls")]
    expected += [("network","rm"),("network","ls"),("volume","inspect")]
    assert commands==expected
@pytest.mark.parametrize("mutation",["missing","reordered"])
def test_generation_three_rejects_incomplete_or_reordered_lineage_before_reconciliation(tmp_path,monkeypatch,mutation):
    values,cleanup,_,_,_=setup(tmp_path,"generation_continuation_not_started")
    if mutation=="missing":values["generation_lineage_finalization_files"].pop()
    else:values["generation_lineage_continuation_files"].reverse()
    monkeypatch.setattr(generation,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail())
    with pytest.raises(generation.DisposablePostgresCleanupGenerationContinueUnavailable):generation.continue_disposable_postgres_cleanup_generation(**values)
    assert cleanup.exists() and values["processes"].calls==[]
def test_generation_three_rejects_open_historical_claim(tmp_path,monkeypatch):
    values,cleanup,_,first,_=setup(tmp_path,"generation_continuation_not_started");prior=json.loads(first[0].read_text());binding=generation._bind(prior,first[0],values["project_name"]);stem=hashlib.sha256(prior["generation_continuation_id"].encode()).hexdigest();_private(values["evidence_directory"]/f".postgres-cleanup-generation-continuation-{stem}.claim",dict(binding,started_at="2026-08-20T14:00:00Z"));monkeypatch.setattr(generation,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail())
    with pytest.raises(generation.DisposablePostgresCleanupGenerationContinueUnavailable):generation.continue_disposable_postgres_cleanup_generation(**values)
    assert cleanup.exists() and values["processes"].calls==[]
def test_lineage_cap_fails_before_historical_reads(tmp_path,monkeypatch):
    values,_,_,_,auth=setup(tmp_path,"generation_continuation_not_started");auth.update(generation=18,predecessor_generation=17);values["generation_continuation_file"]=_private(tmp_path/"generation-eighteen.json",auth);values["generation_lineage_continuation_files"]=[Path("unused-continuation")]*17;values["generation_lineage_finalization_files"]=[Path("unused-finalization")]*17;monkeypatch.setattr(generation,"_historical_generation",lambda _:pytest.fail())
    with pytest.raises(generation.DisposablePostgresCleanupGenerationContinueUnavailable):generation.continue_disposable_postgres_cleanup_generation(**values)
