import hashlib,json
from pathlib import Path
import pytest
import liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize as final
from tests.test_lq331_disposable_postgres_reconciliation import NOW
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq379_disposable_postgres_cleanup_generation_lineage_reconciliation import setup
def prepare(tmp_path:Path):
    values,cleanup,claim,_,_,_=setup(tmp_path,"generation_continuation_not_started");reconciliation=json.loads(values["generation_reconciliation_file"].read_text());authorization={"schema_version":1,"generation_finalization_id":"generation-finalization-380",**{k:reconciliation[k] for k in final.HIST},"generation_reconciliation_authorization_sha256":hashlib.sha256(values["generation_reconciliation_file"].read_bytes()).hexdigest(),"operation":"finalize_disposable_postgres_cleanup_generation_continuation","scope":"runtime_only","executor_id":"generation-three-finalizer","authorizer_id":"lineage-finalization-authorizer","valid_from":"2026-08-20T13:30:00Z","valid_until":"2026-08-20T14:30:00Z"};values["generation_finalization_file"]=_private(tmp_path/"generation-three-finalization.json",authorization);values["clock"]=lambda:NOW;return values,cleanup,claim
def observed(monkeypatch,state,calls=None):
    def inspect(**_):
        if calls is not None:calls.append(state)
        return (json.dumps({"operation":"disposable_postgres_cleanup_generation_continuation_reconciliation","outcome":state,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
    monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_generation_continuation",inspect)
def history(values):return [p.read_bytes() for p in values["generation_lineage_continuation_files"]+values["generation_lineage_finalization_files"]]
@pytest.mark.parametrize("state,outcome",[("generation_continuation_evidence_present","generation_continuation_evidence_confirmed"),("generation_continuation_not_started","generation_continuation_attempt_finalized"),("application_network_removed","later_prefix_finalized"),("runtime_removed_evidence_missing","runtime_removal_ready_for_cleanup_finalization")])
def test_generation_three_writes_evidence_before_releasing_only_current_claim(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);before=history(values);observed(monkeypatch,state);assert json.loads(final.finalize_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]==outcome;stem=hashlib.sha256(b"generation-finalization-380").hexdigest();record=json.loads((values["evidence_directory"]/f"postgres-cleanup-generation-continuation-finalization-{stem}.json").read_text());assert record["observed_state"]==state and record["outcome"]==outcome and record["generation"]==3 and cleanup.exists() and not claim.exists() and history(values)==before
@pytest.mark.parametrize("state,outcome",[("not_found","not_found"),("conflict","investigation_required")])
def test_generation_three_neutral_states_keep_claim_and_lineage(tmp_path,monkeypatch,state,outcome):
    values,cleanup,claim=prepare(tmp_path);before=history(values);observed(monkeypatch,state);assert json.loads(final.finalize_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]==outcome and cleanup.exists() and claim.exists() and history(values)==before;stem=hashlib.sha256(b"generation-finalization-380").hexdigest();assert not (values["evidence_directory"]/f"postgres-cleanup-generation-continuation-finalization-{stem}.json").exists()
def test_generation_three_evidence_retry_skips_inspector_and_releases_claim(tmp_path,monkeypatch):
    values,cleanup,claim=prepare(tmp_path);calls=[];observed(monkeypatch,"application_network_removed",calls);original=final.os.unlink;failed={"value":False}
    def unlink(path):
        if path==claim and not failed["value"]:failed["value"]=True;raise OSError
        return original(path)
    monkeypatch.setattr(final.os,"unlink",unlink)
    with pytest.raises(final.DisposablePostgresCleanupGenerationContinueFinalizeUnavailable):final.finalize_disposable_postgres_cleanup_generation_continuation(**values)
    monkeypatch.setattr(final.os,"unlink",original);monkeypatch.setattr(final,"reconcile_disposable_postgres_cleanup_generation_continuation",lambda **_:pytest.fail());assert json.loads(final.finalize_disposable_postgres_cleanup_generation_continuation(**values))["outcome"]=="later_prefix_finalized" and cleanup.exists() and not claim.exists() and calls==["application_network_removed"]
