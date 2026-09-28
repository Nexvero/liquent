import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_chained_continue as chain
import liquent_platform.operators.disposable_postgres_cleanup_recontinue_finalize as last
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq345_disposable_postgres_cleanup_continuation import _processes
from tests.test_lq355_disposable_postgres_cleanup_recontinuation_finalization import prepare
def setup(tmp_path,state):
    values,cleanup,old=prepare(tmp_path);original=last.reconcile_disposable_postgres_cleanup_recontinuation;last.reconcile_disposable_postgres_cleanup_recontinuation=lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_recontinuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    try:last.finalize_disposable_postgres_cleanup_recontinuation(**values)
    finally:last.reconcile_disposable_postgres_cleanup_recontinuation=original
    la=json.loads(values["recontinuation_finalization_file"].read_text());ls=hashlib.sha256(b"recontinuation-finalization-355").hexdigest();le=values["evidence_directory"]/f"postgres-cleanup-recontinuation-finalization-{ls}.json";effective=la["resume_from"] if state=="recontinuation_not_started" else "application_network_removed"
    auth={"schema_version":1,"chained_continuation_id":"chained-continuation-358",**{k:la[k] for k in chain.CHAIN},"recontinuation_finalization_authorization_sha256":hashlib.sha256(values["recontinuation_finalization_file"].read_bytes()).hexdigest(),"recontinuation_finalization_evidence_sha256":hashlib.sha256(le.read_bytes()).hexdigest(),"previous_resume_from":la["resume_from"],"operation":"continue_disposable_postgres_cleanup_from_finalized_recontinuation","scope":"runtime_only","resume_from":effective,"executor_id":"chain-executor","authorizer_id":"chain-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["chained_continuation_file"]=_private(tmp_path/"chain.json",auth);values["clock"]=lambda:NOW;values["processes"]=_processes(effective);return values,cleanup,effective
def observed(monkeypatch,state):monkeypatch.setattr(chain,"reconcile_disposable_postgres_cleanup",lambda **_:(json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode())
@pytest.mark.parametrize("final_state,effective",[("recontinuation_not_started","container_removed"),("application_network_removed","application_network_removed")])
def test_two_derived_minimal_budgets(tmp_path,monkeypatch,final_state,effective):
    values,cleanup,derived=setup(tmp_path,final_state);assert derived==effective;observed(monkeypatch,effective);result=chain.continue_disposable_postgres_cleanup_chain(**values);assert json.loads(result)["outcome"]=="runtime_removed_pending_cleanup_finalization" and cleanup.exists();commands=[c[0][1:3] for c in values["processes"].calls];expected=[]
    if effective=="container_removed":expected += [("network","rm"),("network","ls")]
    expected += [("network","rm"),("network","ls"),("volume","inspect")]
    assert commands==expected and not any("container" in c[0] for c in values["processes"].calls)
def test_state_mismatch_rejects_before_claim_and_docker(tmp_path,monkeypatch):
    values,_,_=setup(tmp_path,"recontinuation_not_started");observed(monkeypatch,"application_network_removed");assert json.loads(chain.continue_disposable_postgres_cleanup_chain(**values))["outcome"]=="rejected" and values["processes"].calls==[]
