import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue as generation
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue_reconcile as inspect
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import Processes,_private
from tests.test_lq365_disposable_postgres_cleanup_generation_continuation import setup as base,observed as initial_observed
def setup(tmp_path:Path,final_state):
    values,cleanup,effective=base(tmp_path,final_state);initial_observed(pytest.MonkeyPatch(),effective);values["processes"]=Processes([])
    with pytest.raises(generation.DisposablePostgresCleanupGenerationContinueUnavailable):generation.continue_disposable_postgres_cleanup_generation(**values)
    auth=json.loads(values["generation_continuation_file"].read_text());bind=generation._bind(auth,values["generation_continuation_file"],values["project_name"]);stem=hashlib.sha256(auth["generation_continuation_id"].encode()).hexdigest();claim=values["evidence_directory"]/f".postgres-cleanup-generation-continuation-{stem}.claim";ra={"schema_version":1,"generation_reconciliation_id":"generation-reconciliation-367",**{k:auth[k] for k in inspect.COMPARE},"generation_continuation_authorization_sha256":hashlib.sha256(values["generation_continuation_file"].read_bytes()).hexdigest(),"operation":"inspect_disposable_postgres_cleanup_generation_continuation","scope":"runtime_only","executor_id":"generation-inspector","authorizer_id":"inspection-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["generation_reconciliation_file"]=_private(tmp_path/"generation-reconciliation.json",ra);values["clock"]=lambda:NOW;return values,cleanup,claim,bind,stem,effective
def observed(monkeypatch,state,calls=None):
    def run(**_):
        if calls is not None:calls.append(state)
        return (json.dumps({"operation":"disposable_postgres_runtime_cleanup_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",run)
@pytest.mark.parametrize("final_state,state,outcome",[("chained_continuation_not_started","container_removed","generation_continuation_not_started"),("chained_continuation_not_started","application_network_removed","application_network_removed"),("chained_continuation_not_started","runtime_removed_evidence_missing","runtime_removed_evidence_missing"),("application_network_removed","application_network_removed","generation_continuation_not_started"),("application_network_removed","runtime_removed_evidence_missing","runtime_removed_evidence_missing"),("application_network_removed","container_removed","conflict"),("chained_continuation_not_started","container_stopped","conflict")])
def test_closed_matrix_is_read_only(tmp_path,monkeypatch,final_state,state,outcome):
    values,cleanup,claim,_,_,_=setup(tmp_path,final_state);calls=[];observed(monkeypatch,state,calls);before=(cleanup.read_bytes(),claim.read_bytes());result=inspect.reconcile_disposable_postgres_cleanup_generation_continuation(**values);assert json.loads(result)["outcome"]==outcome and calls==[state] and before==(cleanup.read_bytes(),claim.read_bytes())
def test_evidence_wins_without_inspector_or_release(tmp_path,monkeypatch):
    values,cleanup,claim,bind,stem,_=setup(tmp_path,"chained_continuation_not_started");_private(values["evidence_directory"]/f"postgres-cleanup-generation-continuation-{stem}.json",dict(bind,started_at="2026-08-20T14:00:00Z",completed_at="2026-08-20T14:01:00Z",outcome="runtime_removed_pending_cleanup_finalization"));monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail());assert json.loads(inspect.reconcile_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]=="generation_continuation_evidence_present" and cleanup.exists() and claim.exists()
def test_missing_claim_is_neutral_without_inspector(tmp_path,monkeypatch):
    values,_,claim,_,_,_=setup(tmp_path,"chained_continuation_not_started");claim.unlink();monkeypatch.setattr(inspect,"reconcile_disposable_postgres_cleanup",lambda **_:pytest.fail());assert json.loads(inspect.reconcile_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]=="not_found"
