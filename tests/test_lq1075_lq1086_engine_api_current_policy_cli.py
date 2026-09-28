from inspect import signature as inspect_signature
import pytest
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools import engine_api_joint_staging_policy_verify as subject
from tests.test_lq1063_lq1074_engine_api_staging_policy import setup
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW

def arguments(paths):
    policy,trust,signature,evidence,receipt,artifacts=paths;names=("policy-file","trust-file","signature-file","evidence-file","receipt-file","render-file","inspect-file","health-file","staging-policy-file","shutdown-file")
    return [item for pair in zip((f"--{name}" for name in names),(policy,trust,signature,evidence,receipt,*artifacts)) for item in (pair[0],str(pair[1]))]

def test_current_verifier_reads_internal_clock_exactly_once(tmp_path,monkeypatch):
    paths=setup(tmp_path);calls=[]
    def clock(): calls.append(None);return NOW
    monkeypatch.setattr(subject,"_utc_now",clock);subject.verify_current(*paths[:5],*paths[5])
    assert calls==[None] and "now" not in inspect_signature(subject.verify_current).parameters

@pytest.mark.parametrize("clock",(lambda:None,lambda:(_ for _ in ()).throw(RuntimeError("clock"))))
def test_invalid_or_failed_clock_is_unavailable(tmp_path,monkeypatch,clock):
    paths=setup(tmp_path);monkeypatch.setattr(subject,"_utc_now",clock)
    with pytest.raises(ManifestHandoffRegistryUnavailable): subject.verify_current(*paths[:5],*paths[5])

def test_cli_accepts_complete_policy_bound_source_set(tmp_path,monkeypatch):
    paths=setup(tmp_path);monkeypatch.setattr(subject,"_utc_now",lambda:NOW);assert subject.main(arguments(paths))==0

@pytest.mark.parametrize("mutation",("missing","unknown","bad-source","clock"))
def test_cli_fails_detail_free_for_every_incomplete_or_unavailable_case(tmp_path,monkeypatch,mutation):
    paths=setup(tmp_path);argv=arguments(paths);monkeypatch.setattr(subject,"_utc_now",lambda:NOW)
    if mutation=="missing": argv=argv[:-2]
    elif mutation=="unknown": argv.extend(("--unknown","x"))
    elif mutation=="bad-source": argv[1]=str(tmp_path/"absent")
    else: monkeypatch.setattr(subject,"_utc_now",lambda:(_ for _ in ()).throw(RuntimeError("clock")))
    assert subject.main(argv)==2
