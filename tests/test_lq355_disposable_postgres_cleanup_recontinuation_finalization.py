import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_recontinue_finalize as final
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq353_disposable_postgres_cleanup_recontinuation_reconciliation import setup

def prepare(tmp_path:Path):
    values,cleanup,claim,_,_=setup(tmp_path);r=json.loads(values["recontinuation_reconciliation_file"].read_text());auth={"schema_version":1,"recontinuation_finalization_id":"recontinuation-finalization-355",**{k:r[k] for k in final.HIST},"recontinuation_reconciliation_authorization_sha256":hashlib.sha256(values["recontinuation_reconciliation_file"].read_bytes()).hexdigest(),"operation":"finalize_disposable_postgres_cleanup_recontinuation","scope":"runtime_only","executor_id":"recontinuation-finalizer","authorizer_id":"finalization-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["recontinuation_finalization_file"]=_private(tmp_path/"recontinuation-finalization.json",auth);values["clock"]=lambda:NOW;return values,cleanup,claim
def observed(monkeypatch,state,calls=None):
    def inspect(**_):
        if calls is not None:calls.append(state)
        return (json.dumps({"operation":"disposable_postgres_cleanup_recontinuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_recontinuation",inspect)
@pytest.mark.parametrize("state,outcome",[("recontinuation_evidence_present","recontinuation_evidence_confirmed"),("recontinuation_not_started","recontinuation_attempt_finalized"),("application_network_removed","later_prefix_finalized"),("runtime_removed_evidence_missing","runtime_removal_ready_for_cleanup_finalization")])
def test_finalizable_states_write_evidence_then_release_only_current_claim(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);observed(monkeypatch,state);result=final.finalize_disposable_postgres_cleanup_recontinuation(**values);assert json.loads(result)["outcome"]==outcome;stem=hashlib.sha256(b"recontinuation-finalization-355").hexdigest();record=json.loads((values["evidence_directory"]/f"postgres-cleanup-recontinuation-finalization-{stem}.json").read_text());assert record["observed_state"]==state and record["outcome"]==outcome and cleanup.exists() and not claim.exists()
@pytest.mark.parametrize("state,outcome",[("not_found","not_found"),("conflict","investigation_required")])
def test_neutral_states_do_not_write_or_release(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);observed(monkeypatch,state);assert json.loads(final.finalize_disposable_postgres_cleanup_recontinuation(**values))["outcome"]==outcome and cleanup.exists() and claim.exists();assert not list(values["evidence_directory"].glob("postgres-cleanup-recontinuation-finalization-*.json"))
def test_evidence_retry_skips_inspector_and_releases_claim(tmp_path,monkeypatch):
    values,cleanup,claim=prepare(tmp_path);calls=[];observed(monkeypatch,"application_network_removed",calls);original=final.os.unlink;failed={"v":False}
    def unlink(path):
        if path==claim and not failed["v"]:failed["v"]=True;raise OSError
        return original(path)
    monkeypatch.setattr(final.os,"unlink",unlink)
    with pytest.raises(final.DisposablePostgresCleanupRecontinueFinalizeUnavailable):final.finalize_disposable_postgres_cleanup_recontinuation(**values)
    monkeypatch.setattr(final.os,"unlink",original);monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_recontinuation",lambda **_:pytest.fail());assert json.loads(final.finalize_disposable_postgres_cleanup_recontinuation(**values))["outcome"]=="later_prefix_finalized" and cleanup.exists() and not claim.exists() and calls==["application_network_removed"]
