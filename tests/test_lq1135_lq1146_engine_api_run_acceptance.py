from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,record_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools import engine_api_joint_staging_one_shot_verify as command
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root,RUN
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def roots(tmp_path):
    source=run_root(tmp_path);acceptance=tmp_path/"accepted-runs";acceptance.mkdir(mode=0o700);return source,acceptance.resolve()

def test_acceptance_marker_is_owner_private_and_non_reusable(tmp_path):
    source,root=roots(tmp_path);snapshot=load_run_bound_source_set(source);value=build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority),snapshot.run_envelope);record_staging_run_acceptance(root,value);marker=root/(RUN+".accepted")
    assert marker.stat().st_mode&0o777==0o600 and json.loads(marker.read_bytes())["run_id"]==RUN and repr(value)=="ManifestHandoffSupervisorEngineApiStagingRunAcceptance()"
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,value)

@pytest.mark.parametrize("mutation",("root-mode","relative","envelope"))
def test_acceptance_rejects_invalid_state_or_binding(tmp_path,mutation):
    source,root=roots(tmp_path);snapshot=load_run_bound_source_set(source);authority=decode_staging_run_authority(snapshot.run_authority);envelope=snapshot.run_envelope
    if mutation=="root-mode": root.chmod(0o750)
    elif mutation=="relative": root=type(root)("accepted-runs")
    else: envelope=envelope.replace(RUN.encode(),b"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    with pytest.raises(ManifestHandoffRegistryUnavailable): record_staging_run_acceptance(root,build_staging_run_acceptance(authority,envelope))

def test_parallel_acceptance_has_exactly_one_success(tmp_path):
    source,root=roots(tmp_path);snapshot=load_run_bound_source_set(source);value=build_staging_run_acceptance(decode_staging_run_authority(snapshot.run_authority),snapshot.run_envelope)
    def attempt():
        try: record_staging_run_acceptance(root,value);return True
        except ManifestHandoffRegistryUnavailable: return False
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:attempt(),range(2)))
    assert sorted(results)==[False,True]

def test_verify_then_accept_is_one_shot(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_and_accept(source,root)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_and_accept(source,root)

def test_failed_verification_does_not_consume_run(tmp_path,monkeypatch):
    source,root=roots(tmp_path);(source/"run-signature").write_bytes(b"invalid\n");monkeypatch.setattr(command,"_utc_now",lambda:NOW)
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_and_accept(source,root)
    assert list(root.iterdir())==[]

def test_one_shot_cli_returns_zero_then_two(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);argv=["--source-root",str(source),"--acceptance-root",str(root)]
    assert command.main(argv)==0 and command.main(argv)==2
