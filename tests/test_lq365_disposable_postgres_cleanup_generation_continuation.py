import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue as generation
import liquent_platform.operators.disposable_postgres_cleanup_chained_continue_finalize as predecessor
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq345_disposable_postgres_cleanup_continuation import _processes
from tests.test_lq362_disposable_postgres_cleanup_chained_continuation_finalization import prepare

def setup(tmp_path:Path,state):
    values,cleanup,_=prepare(tmp_path);original=predecessor.reconcile_disposable_postgres_cleanup_chained_continuation;predecessor.reconcile_disposable_postgres_cleanup_chained_continuation=lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_chained_continuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    try:predecessor.finalize_disposable_postgres_cleanup_chained_continuation(**values)
    finally:predecessor.reconcile_disposable_postgres_cleanup_chained_continuation=original
    last=json.loads(values["chained_finalization_file"].read_text());stem=hashlib.sha256(last["chained_finalization_id"].encode()).hexdigest();evidence=values["evidence_directory"]/f"postgres-cleanup-chained-continuation-finalization-{stem}.json";effective=last["resume_from"] if state=="chained_continuation_not_started" else "application_network_removed";auth={"schema_version":1,"generation_continuation_id":"generation-continuation-365","generation":1,"predecessor_kind":"lq362","predecessor_generation":0,**{k:last[k] for k in generation.ROOT},"predecessor_resume_from":last["resume_from"],"predecessor_finalization_authorization_sha256":hashlib.sha256(values["chained_finalization_file"].read_bytes()).hexdigest(),"predecessor_finalization_evidence_sha256":hashlib.sha256(evidence.read_bytes()).hexdigest(),"operation":"continue_disposable_postgres_cleanup_from_generation","scope":"runtime_only","resume_from":effective,"executor_id":"generation-executor","authorizer_id":"generation-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["generation_continuation_file"]=_private(tmp_path/"generation.json",auth);values.pop("chained_reconciliation_file");values["clock"]=lambda:NOW;values["processes"]=_processes(effective);return values,cleanup,effective
def observed(monkeypatch,state):monkeypatch.setattr(generation,"reconcile_disposable_postgres_cleanup",lambda **_:(json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode())
@pytest.mark.parametrize("final_state,effective",[("chained_continuation_not_started","container_removed"),("application_network_removed","application_network_removed")])
def test_generation_one_uses_direct_lq362_anchor_and_minimal_budget(tmp_path,monkeypatch,final_state,effective):
    values,cleanup,derived=setup(tmp_path,final_state);observed(monkeypatch,effective);result=generation.continue_disposable_postgres_cleanup_generation(**values);assert derived==effective and json.loads(result)["outcome"]=="runtime_removed_pending_cleanup_finalization" and cleanup.exists();commands=[c[0][1:3] for c in values["processes"].calls];expected=[]
    if effective=="container_removed":expected += [("network","rm"),("network","ls")]
    expected += [("network","rm"),("network","ls"),("volume","inspect")]
    assert commands==expected
def test_state_mismatch_rejects_before_claim_and_docker(tmp_path,monkeypatch):
    values,_,_=setup(tmp_path,"chained_continuation_not_started");observed(monkeypatch,"application_network_removed");assert json.loads(generation.continue_disposable_postgres_cleanup_generation(**values))["outcome"]=="rejected" and values["processes"].calls==[]
def test_generation_and_predecessor_hash_are_closed(tmp_path,monkeypatch):
    values,cleanup,_=setup(tmp_path,"chained_continuation_not_started");auth=json.loads(values["generation_continuation_file"].read_text());auth["generation"]=2;_private(values["generation_continuation_file"],auth);monkeypatch.setattr(generation,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail())
    with pytest.raises(generation.DisposablePostgresCleanupGenerationContinueUnavailable):generation.continue_disposable_postgres_cleanup_generation(**values)
    assert cleanup.exists() and values["processes"].calls==[]
