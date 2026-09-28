from dataclasses import replace
import json
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,decode_staging_run_acceptance,encode_staging_run_acceptance,load_staging_run_acceptance,record_staging_run_acceptance,verify_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools import engine_api_joint_staging_one_shot_verify as command
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def value(source):
    snapshot=load_run_bound_source_set(source);authority=decode_staging_run_authority(snapshot.run_authority);return authority,snapshot.run_envelope,build_staging_run_acceptance(authority,snapshot.run_envelope)

def test_acceptance_codec_round_trip(tmp_path):
    source,_=roots(tmp_path);_,_,acceptance=value(source);assert decode_staging_run_acceptance(encode_staging_run_acceptance(acceptance))==acceptance

@pytest.mark.parametrize("mutation",("extra","noncanonical","wrong-run","wrong-hash"))
def test_acceptance_decoder_or_binding_rejects_mutation(tmp_path,mutation):
    source,_=roots(tmp_path);authority,envelope,acceptance=value(source);content=encode_staging_run_acceptance(acceptance)
    if mutation=="extra": content=content[:-2]+b',"extra":true}\n'
    elif mutation=="noncanonical": content=content.replace(b'":',b'": ')
    elif mutation=="wrong-run": acceptance=replace(acceptance,run_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    else: acceptance=replace(acceptance,envelope_sha256="0"*64)
    if mutation in ("extra","noncanonical"):
        with pytest.raises(ManifestHandoffRegistryUnavailable): decode_staging_run_acceptance(content)
    else:
        with pytest.raises(ManifestHandoffRegistryUnavailable): verify_staging_run_acceptance(acceptance,authority,envelope)

def test_lookup_distinguishes_absence_from_valid_marker(tmp_path):
    source,root=roots(tmp_path);authority,envelope,acceptance=value(source);assert load_staging_run_acceptance(root,RUN) is None;record_staging_run_acceptance(root,acceptance);loaded=load_staging_run_acceptance(root,RUN);verify_staging_run_acceptance(loaded,authority,envelope)

@pytest.mark.parametrize("mutation",("mode","content","link","root-mode"))
def test_lookup_treats_corrupt_or_unsafe_marker_as_unavailable(tmp_path,mutation):
    source,root=roots(tmp_path);_,_,acceptance=value(source);record_staging_run_acceptance(root,acceptance);marker=root/(RUN+".accepted")
    if mutation=="mode": marker.chmod(0o640)
    elif mutation=="content": marker.write_bytes(b"invalid\n")
    elif mutation=="link": (tmp_path/"linked").hardlink_to(marker)
    else: root.chmod(0o750)
    with pytest.raises(ManifestHandoffRegistryUnavailable): load_staging_run_acceptance(root,RUN)

def test_existing_valid_marker_stops_before_clock_and_crypto(tmp_path,monkeypatch):
    source,root=roots(tmp_path);_,_,acceptance=value(source);record_staging_run_acceptance(root,acceptance);monkeypatch.setattr(command,"_utc_now",lambda:(_ for _ in ()).throw(AssertionError("clock must not run")))
    with pytest.raises(ManifestHandoffRegistryUnavailable): command.verify_and_accept(source,root)

def test_absent_marker_allows_one_acceptance(tmp_path,monkeypatch):
    source,root=roots(tmp_path);monkeypatch.setattr(command,"_utc_now",lambda:NOW);command.verify_and_accept(source,root);assert load_staging_run_acceptance(root,RUN) is not None
