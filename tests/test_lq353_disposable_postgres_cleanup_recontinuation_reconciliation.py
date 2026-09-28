import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_continue_finalize as fin
import liquent_platform.operators.disposable_postgres_cleanup_recontinue as again
import liquent_platform.operators.disposable_postgres_cleanup_recontinue_reconcile as inspect
from tests.test_lq331_disposable_postgres_reconciliation import NOW,PROJECT
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq349_disposable_postgres_cleanup_continuation_finalization import _setup

def setup(tmp_path:Path,resume="container_removed"):
    values,cleanup_claim,old_claim=_setup(tmp_path,"container_stopped")
    monkey_state=resume
    original=fin.reconcile_disposable_postgres_cleanup_continuation
    fin.reconcile_disposable_postgres_cleanup_continuation=lambda **_:(json.dumps({"operation":"disposable_postgres_cleanup_continuation_reconciliation","outcome":monkey_state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    try: fin.finalize_disposable_postgres_cleanup_continuation(**values)
    finally: fin.reconcile_disposable_postgres_cleanup_continuation=original
    fa=json.loads(values["continuation_finalization_file"].read_text());fs=hashlib.sha256(b"continuation-finalization-349").hexdigest();fe=values["evidence_directory"]/f"postgres-cleanup-continuation-finalization-{fs}.json"
    ra={"schema_version":1,"recontinuation_id":"recontinuation-351",**{k:fa[k] for k in again.BASE},"continuation_finalization_authorization_sha256":hashlib.sha256(values["continuation_finalization_file"].read_bytes()).hexdigest(),"continuation_finalization_evidence_sha256":hashlib.sha256(fe.read_bytes()).hexdigest(),"operation":"continue_disposable_postgres_cleanup_from_finalized_prefix","scope":"runtime_only","resume_from":resume,"executor_id":"recontinuation-executor","authorizer_id":"recontinuation-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"}
    rf=_private(tmp_path/"recontinuation.json",ra);bind=again._binding2(ra,rf,PROJECT);stem=hashlib.sha256(b"recontinuation-351").hexdigest();claim=_private(values["evidence_directory"]/f".postgres-cleanup-recontinuation-{stem}.claim",dict(bind,started_at="2026-08-20T14:00:00Z"))
    ca={"schema_version":1,"recontinuation_reconciliation_id":"recontinuation-reconciliation-353",**{k:ra[k] for k in ("recontinuation_id",*again.BASE,"continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","scope","resume_from")},"recontinuation_authorization_sha256":hashlib.sha256(rf.read_bytes()).hexdigest(),"operation":"inspect_disposable_postgres_cleanup_recontinuation","executor_id":"recontinuation-inspector","authorizer_id":"inspection-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"}
    values["recontinuation_file"]=rf;values["recontinuation_reconciliation_file"]=_private(tmp_path/"recontinuation-reconciliation.json",ca);values["clock"]=lambda:NOW
    return values,cleanup_claim,claim,bind,stem
def observed(monkeypatch,state,calls):
    def run(**_):calls.append(state);return (json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",run)
@pytest.mark.parametrize("resume,state,outcome",[("container_removed","container_removed","recontinuation_not_started"),("container_removed","application_network_removed","application_network_removed"),("container_removed","runtime_removed_evidence_missing","runtime_removed_evidence_missing"),("application_network_removed","application_network_removed","recontinuation_not_started"),("application_network_removed","runtime_removed_evidence_missing","runtime_removed_evidence_missing"),("application_network_removed","container_removed","conflict"),("container_removed","container_stopped","conflict")])
def test_prefix_matrix_is_read_only(tmp_path,monkeypatch,resume,state,outcome):
    values,cleanup,claim,_,_=setup(tmp_path,resume);calls=[];observed(monkeypatch,state,calls);before=(cleanup.read_bytes(),claim.read_bytes());result=inspect.reconcile_disposable_postgres_cleanup_recontinuation(**values);assert json.loads(result)["outcome"]==outcome and calls==[state] and before==(cleanup.read_bytes(),claim.read_bytes())
def test_evidence_and_absence_short_circuit(tmp_path,monkeypatch):
    values,cleanup,claim,bind,stem=setup(tmp_path);_private(values["evidence_directory"]/f"postgres-cleanup-recontinuation-{stem}.json",dict(bind,started_at="2026-08-20T14:00:00Z",completed_at="2026-08-20T14:01:00Z",outcome="runtime_removed_pending_cleanup_finalization"));monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail());assert json.loads(inspect.reconcile_disposable_postgres_cleanup_recontinuation(**values))["outcome"]=="recontinuation_evidence_present";claim.unlink();assert json.loads(inspect.reconcile_disposable_postgres_cleanup_recontinuation(**values))["outcome"]=="recontinuation_evidence_present" and cleanup.exists()
def test_no_claim_is_not_found_without_inspection(tmp_path,monkeypatch):
    values,_,claim,_,_=setup(tmp_path);claim.unlink();monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail());assert json.loads(inspect.reconcile_disposable_postgres_cleanup_recontinuation(**values))["outcome"]=="not_found"
