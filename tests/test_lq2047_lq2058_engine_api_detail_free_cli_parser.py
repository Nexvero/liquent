import pytest
from tests.test_lq1039_lq1050_engine_api_staging_receipt import NOW
from tests.test_lq1195_lq1206_engine_api_operation_root import operation_root
from tools import engine_api_joint_staging_acceptance_audit as audit_subject
from tools import engine_api_joint_staging_one_shot_verify as accept_subject
from tools import engine_api_joint_staging_operation_verify as subject

@pytest.mark.parametrize("argv",((),("--operation-root","/tmp/root"),("--mode","audit-registry"),("--operation-root","/tmp/root","--mode","unknown"),("--unknown","value"),("--help",)))
def test_invalid_cli_input_is_silent_and_returns_two(argv,capsys):
    assert subject.main(list(argv))==2
    captured=capsys.readouterr();assert captured.out==captured.err==""

def test_parser_error_and_exit_are_detail_free(capsys):
    parser=subject._DetailFreeArgumentParser(add_help=False);parser.add_argument("--required",required=True)
    with pytest.raises(Exception): parser.parse_args([])
    with pytest.raises(Exception): parser.exit(2,"secret")
    captured=capsys.readouterr();assert captured.out==captured.err==""

@pytest.mark.parametrize("mode",("audit-registry","accept-once","audit-accepted-source"))
def test_valid_cli_modes_remain_silent_and_successful(tmp_path,monkeypatch,mode,capsys):
    root=operation_root(tmp_path);monkeypatch.setattr(accept_subject,"_utc_now",lambda:NOW);monkeypatch.setattr(audit_subject,"_utc_now",lambda:NOW)
    if mode=="audit-accepted-source": subject.accept_once(root)
    assert subject.main(["--operation-root",str(root),"--mode",mode])==0
    captured=capsys.readouterr();assert captured.out==captured.err==""

def test_cli_operation_failure_remains_silent(tmp_path,monkeypatch,capsys):
    root=operation_root(tmp_path);monkeypatch.setattr(subject,"audit",lambda *args,**kwargs:(_ for _ in ()).throw(ValueError("secret")))
    assert subject.main(["--operation-root",str(root),"--mode","audit-registry"])==2
    captured=capsys.readouterr();assert captured.out==captured.err==""
