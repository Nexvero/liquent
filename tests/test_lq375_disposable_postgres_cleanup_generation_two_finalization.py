import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize as final
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq373_disposable_postgres_cleanup_generation_two_reconciliation import setup
def prepare(tmp_path:Path):
    values,cleanup,claim,_,_,_=setup(tmp_path,"generation_continuation_not_started");r=json.loads(values["generation_reconciliation_file"].read_text());auth={"schema_version":1,"generation_finalization_id":"generation-finalization-375",**{k:r[k] for k in final.HIST},"generation_reconciliation_authorization_sha256":hashlib.sha256(values["generation_reconciliation_file"].read_bytes()).hexdigest(),"operation":"finalize_disposable_postgres_cleanup_generation_continuation","scope":"runtime_only","executor_id":"generation-two-finalizer","authorizer_id":"finalization-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["generation_finalization_file"]=_private(tmp_path/"generation-two-finalization.json",auth);values["clock"]=lambda:NOW;return values,cleanup,claim
def observed(monkeypatch,state,calls=None):
    def inspect(**_):
        if calls is not None:calls.append(state)
        return (json.dumps({"operation":"disposable_postgres_cleanup_generation_continuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_generation_continuation",inspect)
@pytest.mark.parametrize("state,outcome",[("generation_continuation_evidence_present","generation_continuation_evidence_confirmed"),("generation_continuation_not_started","generation_continuation_attempt_finalized"),("application_network_removed","later_prefix_finalized"),("runtime_removed_evidence_missing","runtime_removal_ready_for_cleanup_finalization")])
def test_generation_two_states_write_evidence_then_release_only_current_claim(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);observed(monkeypatch,state);result=final.finalize_disposable_postgres_cleanup_generation_continuation(**values);assert json.loads(result)["outcome"]==outcome;stem=hashlib.sha256(b"generation-finalization-375").hexdigest();record=json.loads((values["evidence_directory"]/f"postgres-cleanup-generation-continuation-finalization-{stem}.json").read_text());assert record["observed_state"]==state and record["outcome"]==outcome and record["generation"]==2 and cleanup.exists() and not claim.exists()
@pytest.mark.parametrize("state,outcome",[("not_found","not_found"),("conflict","investigation_required")])
def test_generation_two_neutral_states_do_not_write_or_release(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);observed(monkeypatch,state);assert json.loads(final.finalize_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]==outcome and cleanup.exists() and claim.exists();stem=hashlib.sha256(b"generation-finalization-375").hexdigest();assert not (values["evidence_directory"]/f"postgres-cleanup-generation-continuation-finalization-{stem}.json").exists()
def test_generation_two_evidence_retry_skips_inspector_and_releases_claim(tmp_path,monkeypatch):
    values,cleanup,claim=prepare(tmp_path);calls=[];observed(monkeypatch,"application_network_removed",calls);original=final.os.unlink;failed={"v":False}
    def unlink(path):
        if path==claim and not failed["v"]:failed["v"]=True;raise OSError
        return original(path)
    monkeypatch.setattr(final.os,"unlink",unlink)
    with pytest.raises(final.DisposablePostgresCleanupGenerationContinueFinalizeUnavailable):final.finalize_disposable_postgres_cleanup_generation_continuation(**values)
    monkeypatch.setattr(final.os,"unlink",original);monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_generation_continuation",lambda **_:pytest.fail());assert json.loads(final.finalize_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]=="later_prefix_finalized" and cleanup.exists() and not claim.exists() and calls==["application_network_removed"]
