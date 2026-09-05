"""Owner-controlled cleanup continuation chained from LQ-355 evidence."""
from __future__ import annotations
import argparse,hashlib,json,os,stat,sys
from datetime import UTC,datetime,timedelta
from pathlib import Path
from liquent_platform.operators.disposable_postgres_cleanup_continue import _continuation_claim,_evidence_binding as _old_binding
from liquent_platform.operators.disposable_postgres_cleanup_continue_finalize import _evidence_binding as _prior_binding,_existing as _prior_existing
from liquent_platform.operators.disposable_postgres_cleanup_finalize import _historical_reconciliation
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import _claim,_historical_cleanup,reconcile_disposable_postgres_cleanup
from liquent_platform.operators.disposable_postgres_cleanup_recontinue import BASE,_artifact,_binding2,_historical_final
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_finalize import HIST,_authorization as _last_auth,_binding3,_existing as _last_existing
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_reconcile import _historical_recontinuation
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root,_historical,_observe,_owned_volume,_pairs,_timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _absent,_binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT,IMAGE,OPAQUE,SHA256
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner
STEPS={"container_removed":["application_network_absent","data_network_absent"],"application_network_removed":["data_network_absent"]}
CHAIN=("recontinuation_finalization_id",*(k for k in HIST if k!="resume_from"),"recontinuation_reconciliation_authorization_sha256")
KEYS={"schema_version","chained_continuation_id",*CHAIN,"recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","previous_resume_from","operation","scope","resume_from","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupChainedContinueUnavailable(Exception):
    code="disposable_postgres_cleanup_chained_continue_unavailable"
    def __init__(self):super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_):raise DisposablePostgresCleanupChainedContinueUnavailable
def _auth(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="continue_disposable_postgres_cleanup_from_finalized_recontinuation" or v["resume_from"] not in STEPS or v["previous_resume_from"] not in STEPS:raise ValueError
        for k in ("chained_continuation_id","recontinuation_finalization_id","recontinuation_reconciliation_id","recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]):raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]):raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","recontinuation_authorization_sha256","recontinuation_reconciliation_authorization_sha256","recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]):raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b:raise ValueError
        return v
    except Exception:raise DisposablePostgresCleanupChainedContinueUnavailable from None
def _historical_last(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _last_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupChainedContinueUnavailable from None
def _bind(v,path,project):return {"schema_version":1,**{k:v[k] for k in ("chained_continuation_id",*CHAIN,"recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","previous_resume_from","scope","resume_from","executor_id","authorizer_id")},"chained_continuation_authorization_sha256":hashlib.sha256(_private_file(path,32768)).hexdigest(),"container":f"{project}-postgres-1","application_network":f"{project}-application","data_network":f"{project}-data","retained_volume":f"{project}-postgres-data","remaining_steps":STEPS[v["resume_from"]]+["data_volume_retained"]}
def _file(path,binding,final=False):
    try:
        if not path.exists():return False
        m=path.stat(follow_symlinks=False);v=json.loads(path.read_bytes(),object_pairs_hook=_pairs);extra={"started_at","completed_at","outcome"} if final else {"started_at"}
        if not stat.S_ISREG(m.st_mode) or m.st_uid!=os.geteuid() or m.st_nlink!=1 or stat.S_IMODE(m.st_mode)!=0o600 or type(v) is not dict or set(v)!=set(binding)|extra or any(v[k]!=x for k,x in binding.items()) or (final and v["outcome"]!="runtime_removed_pending_cleanup_finalization"):raise ValueError
        return True
    except Exception:raise DisposablePostgresCleanupChainedContinueUnavailable from None
def _write(root,fd,path,record):
    temp=root/f".{path.stem}-{os.getpid()}.tmp";opened=None
    try:data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode();opened=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.write(opened,data);os.fsync(opened);os.close(opened);opened=None;os.link(temp,path);temp.unlink();os.fsync(fd);b={k:v for k,v in record.items() if k not in {"started_at","completed_at","outcome"}};assert _file(path,b,True)
    except Exception:raise DisposablePostgresCleanupChainedContinueUnavailable from None
    finally:
        if opened is not None:os.close(opened)
        try:temp.unlink()
        except FileNotFoundError:pass
def _result(outcome):return (json.dumps({"operation":"disposable_postgres_runtime_cleanup_chained_continuation","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def continue_disposable_postgres_cleanup_chain(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,recontinuation_reconciliation_file,recontinuation_finalization_file,chained_continuation_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,processes=None,clock=lambda:datetime.now(UTC)):
    fd=None
    try:
        original=_historical(authorization_file);cleanup=_historical_cleanup(cleanup_file);recon=_historical_reconciliation(cleanup_reconciliation_file);old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs);recont=_historical_recontinuation(recontinuation_file);last=_historical_last(recontinuation_finalization_file);current=_auth(chained_continuation_file,clock)
        if current["recontinuation_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(recontinuation_finalization_file,32768)).hexdigest() or any(current[k]!=last[k] for k in CHAIN) or current["previous_resume_from"]!=last["resume_from"] or original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}" or not docker_executable.is_absolute() or not docker_executable.is_file() or not os.access(docker_executable,os.X_OK):raise ValueError
        lb=_binding3(last,recontinuation_finalization_file);ls=hashlib.sha256(last["recontinuation_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-recontinuation-finalization-{ls}.json";out=_last_existing(lp,lb)
        if current["recontinuation_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(lp,32768)).hexdigest() or out not in {"recontinuation_attempt_finalized","later_prefix_finalized"}:raise ValueError
        expected=last["resume_from"] if out=="recontinuation_attempt_finalized" else "application_network_removed"
        if current["resume_from"]!=expected:raise ValueError
        cbind=_binding(original,cleanup,cleanup_file,project_name);cs=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cs}.claim",cbind):raise ValueError
        ob=_old_binding(old,cleanup_continuation_file,project_name);osx=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest();oc=evidence_directory/f".postgres-cleanup-continuation-{osx}.claim"
        if oc.exists():_continuation_claim(oc,ob);raise ValueError
        rb=_binding2(recont,recontinuation_file,project_name);rs=hashlib.sha256(recont["recontinuation_id"].encode()).hexdigest();rc=evidence_directory/f".postgres-cleanup-recontinuation-{rs}.claim"
        if rc.exists():_artifact(rc,rb);raise ValueError
        bind=_bind(current,chained_continuation_file,project_name);stem=hashlib.sha256(current["chained_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-chained-continuation-{stem}.claim";final=evidence_directory/f"postgres-cleanup-chained-continuation-{stem}.json";fd=_evidence_root(evidence_directory)
        if _file(final,bind,True):
            if claim.exists() and not _file(claim,bind):raise ValueError
            if claim.exists():os.unlink(claim);os.fsync(fd)
            return _result("runtime_removed_pending_cleanup_finalization")
        if claim.exists():raise ValueError
        a,b=_timestamp(recon["valid_from"]),_timestamp(recon["valid_until"]);raw=reconcile_disposable_postgres_cleanup(docker_executable=docker_executable,authorization_file=authorization_file,reconciliation_file=reconciliation_file,claim_reconciliation_file=claim_reconciliation_file,disposition_file=disposition_file,cleanup_file=cleanup_file,cleanup_reconciliation_file=cleanup_reconciliation_file,staging_evidence_file=staging_evidence_file,compose_file=compose_file,runtime_environment_file=runtime_environment_file,image_environment_file=image_environment_file,project_name=project_name,evidence_directory=evidence_directory,processes=processes,clock=lambda:a+(b-a)/2);obs=json.loads(raw,object_pairs_hook=_pairs)
        if set(obs)!={"schema_version","operation","outcome"} or obs["operation"]!="disposable_postgres_runtime_cleanup_reconciliation" or obs["outcome"]!=current["resume_from"]:return _result("rejected")
        started=clock().astimezone(UTC).isoformat().replace("+00:00","Z");data=(json.dumps(dict(bind,started_at=started),sort_keys=True,separators=(",",":"))+"\n").encode();opened=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.write(opened,data);os.fsync(opened);os.close(opened);os.fsync(fd);runner=processes or LocalBoundedProcessRunner();docker=str(docker_executable);nets=(bind["application_network"],bind["data_network"]);first=0 if current["resume_from"]=="container_removed" else 1
        for name in nets[first:]:_observe(runner,(docker,"network","rm",name),maximum=65536);absent=_observe(runner,(docker,"network","ls","--filter",f"name=^{name}$","--format","{{.Name}}"),maximum=65536).stdout;assert _absent(absent)
        assert _owned_volume(_observe(runner,(docker,"volume","inspect",bind["retained_volume"]),maximum=1048576).stdout,name=bind["retained_volume"],project=project_name);record=dict(bind,started_at=started,completed_at=clock().astimezone(UTC).isoformat().replace("+00:00","Z"),outcome="runtime_removed_pending_cleanup_finalization");_write(evidence_directory,fd,final,record);assert _file(claim,bind);os.unlink(claim);os.fsync(fd);return _result("runtime_removed_pending_cleanup_finalization")
    except DisposablePostgresCleanupChainedContinueUnavailable:raise
    except Exception:raise DisposablePostgresCleanupChainedContinueUnavailable from None
    finally:
        if fd is not None:os.close(fd)
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-chain-continue",add_help=False);names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","recontinuation-reconciliation-file","recontinuation-finalization-file","chained-continuation-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--project-name",required=True)
    try:v=vars(p.parse_args(argv));v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(continue_disposable_postgres_cleanup_chain(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
