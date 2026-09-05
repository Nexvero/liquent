import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_continue_finalize as fin
import liquent_platform.operators.disposable_postgres_cleanup_recontinue as again
from tests.test_lq331_disposable_postgres_reconciliation import NOW,PROJECT
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq345_disposable_postgres_cleanup_continuation import _observed as old_observed,_processes
from tests.test_lq349_disposable_postgres_cleanup_continuation_finalization import _setup

def observed(monkeypatch,state):
    monkeypatch.setattr(again,"reconcile_disposable_postgres_cleanup",lambda **_:(json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode())

@pytest.mark.parametrize("state",["container_removed","application_network_removed"])
def test_two_minimal_recontinuation_budgets(tmp_path:Path,monkeypatch,state):
    values,cleanup_claim,old_claim=_setup(tmp_path,"container_stopped")
    monkeypatch.setattr(fin,"reconcile_disposable_postgres_cleanup_continuation",lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_continuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode())
    fin.finalize_disposable_postgres_cleanup_continuation(**values)
    assert not old_claim.exists()
    fa=json.loads(values["continuation_finalization_file"].read_text()); stem=hashlib.sha256(b"continuation-finalization-349").hexdigest(); evidence=values["evidence_directory"]/f"postgres-cleanup-continuation-finalization-{stem}.json"
    current={"schema_version":1,"recontinuation_id":"recontinuation-351",**{k:fa[k] for k in again.BASE},"continuation_finalization_authorization_sha256":hashlib.sha256(values["continuation_finalization_file"].read_bytes()).hexdigest(),"continuation_finalization_evidence_sha256":hashlib.sha256(evidence.read_bytes()).hexdigest(),"operation":"continue_disposable_postgres_cleanup_from_finalized_prefix","scope":"runtime_only","resume_from":state,"executor_id":"recontinuation-executor","authorizer_id":"recontinuation-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"}
    values["recontinuation_file"]=_private(tmp_path/"recontinuation.json",current); values["processes"]=_processes(state); values["clock"]=lambda:NOW; observed(monkeypatch,state)
    result=again.recontinue_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"]=="runtime_removed_pending_cleanup_finalization"
    commands=[call[0][1:3] for call in values["processes"].calls]
    expected=[]
    if state=="container_removed": expected += [("network","rm"),("network","ls")]
    expected += [("network","rm"),("network","ls"),("volume","inspect")]
    assert commands==expected and cleanup_claim.exists()
    assert not any("container" in call[0] for call in values["processes"].calls)

def test_state_mismatch_rejects_before_claim_or_docker(tmp_path:Path,monkeypatch):
    values,_,_=_setup(tmp_path,"container_stopped")
    monkeypatch.setattr(fin,"reconcile_disposable_postgres_cleanup_continuation",lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_continuation_reconciliation","outcome":"container_removed","schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode());fin.finalize_disposable_postgres_cleanup_continuation(**values)
    fa=json.loads(values["continuation_finalization_file"].read_text());stem=hashlib.sha256(b"continuation-finalization-349").hexdigest();ev=values["evidence_directory"]/f"postgres-cleanup-continuation-finalization-{stem}.json"
    current={"schema_version":1,"recontinuation_id":"recontinuation-351",**{k:fa[k] for k in again.BASE},"continuation_finalization_authorization_sha256":hashlib.sha256(values["continuation_finalization_file"].read_bytes()).hexdigest(),"continuation_finalization_evidence_sha256":hashlib.sha256(ev.read_bytes()).hexdigest(),"operation":"continue_disposable_postgres_cleanup_from_finalized_prefix","scope":"runtime_only","resume_from":"container_removed","executor_id":"recontinuation-executor","authorizer_id":"recontinuation-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"}
    values["recontinuation_file"]=_private(tmp_path/"recontinuation.json",current);values["processes"]=_processes("container_removed");values["clock"]=lambda:NOW;observed(monkeypatch,"application_network_removed")
    assert json.loads(again.recontinue_disposable_postgres_cleanup(**values))["outcome"]=="rejected" and values["processes"].calls==[]
