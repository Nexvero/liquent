"""Owner-controlled cleanup recontinuation from finalized later-prefix evidence."""
from __future__ import annotations
import argparse, hashlib, json, os, stat, sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from liquent_platform.operators.disposable_postgres_cleanup_continue import _continuation_claim, _evidence_binding as _old_binding
from liquent_platform.operators.disposable_postgres_cleanup_continue_finalize import _authorization as _final_auth, _evidence_binding as _final_binding, _existing as _final_existing
from liquent_platform.operators.disposable_postgres_cleanup_finalize import _historical_reconciliation
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import _claim, _historical_cleanup, reconcile_disposable_postgres_cleanup
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root, _historical, _observe, _owned_volume, _pairs, _timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _absent, _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT, IMAGE, OPAQUE, SHA256
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner

STEPS={"container_removed":["application_network_absent","data_network_absent"],"application_network_removed":["data_network_absent"]}
BASE=("continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","phase","source_commit","image_ref","compose_sha256","reconciliation_id","claim_reconciliation_id","disposition_id","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256")
KEYS={"schema_version","recontinuation_id",*BASE,"continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","operation","scope","resume_from","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupRecontinueUnavailable(Exception):
    code="disposable_postgres_cleanup_recontinue_unavailable"
    def __init__(self): super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_): raise DisposablePostgresCleanupRecontinueUnavailable
def _auth(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="continue_disposable_postgres_cleanup_from_finalized_prefix" or v["resume_from"] not in STEPS: raise ValueError
        for k in ("recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]): raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]): raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]): raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b: raise ValueError
        return v
    except Exception: raise DisposablePostgresCleanupRecontinueUnavailable from None
def _historical_final(path):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs); a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"])
        return _final_auth(path,clock=lambda:a+(b-a)/2)
    except Exception: raise DisposablePostgresCleanupRecontinueUnavailable from None
def _binding2(v,path,project):
    return {"schema_version":1,**{k:v[k] for k in ("recontinuation_id",*BASE,"continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","scope","resume_from","executor_id","authorizer_id")},"recontinuation_authorization_sha256":hashlib.sha256(_private_file(path,32768)).hexdigest(),"container":f"{project}-postgres-1","application_network":f"{project}-application","data_network":f"{project}-data","retained_volume":f"{project}-postgres-data","remaining_steps":STEPS[v["resume_from"]]+["data_volume_retained"]}
def _artifact(path,binding,final=False):
    try:
        if not path.exists(): return False
        m=path.stat(follow_symlinks=False); v=json.loads(path.read_bytes(),object_pairs_hook=_pairs); extra={"started_at","completed_at","outcome"} if final else {"started_at"}
        if not stat.S_ISREG(m.st_mode) or m.st_uid!=os.geteuid() or m.st_nlink!=1 or stat.S_IMODE(m.st_mode)!=0o600 or type(v) is not dict or set(v)!=set(binding)|extra or any(v[k]!=x for k,x in binding.items()) or (final and v["outcome"]!="runtime_removed_pending_cleanup_finalization"): raise ValueError
        for k in extra-{"outcome"}:
            if datetime.fromisoformat(v[k].replace("Z","+00:00")).tzinfo is None: raise ValueError
        return True
    except Exception: raise DisposablePostgresCleanupRecontinueUnavailable from None
def _write(root,fd,path,record):
    temp=root/f".{path.stem}-{os.getpid()}.tmp"; opened=None
    try:
        data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode(); opened=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600); os.write(opened,data); os.fsync(opened); os.close(opened); opened=None; os.link(temp,path); temp.unlink(); os.fsync(fd)
        b={k:v for k,v in record.items() if k not in {"started_at","completed_at","outcome"}}
        if not _artifact(path,b,True): raise ValueError
    except Exception: raise DisposablePostgresCleanupRecontinueUnavailable from None
    finally:
        if opened is not None: os.close(opened)
        try: temp.unlink()
        except FileNotFoundError: pass
def _result(outcome): return (json.dumps({"operation":"disposable_postgres_runtime_cleanup_recontinuation","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def recontinue_disposable_postgres_cleanup(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,processes=None,clock=lambda:datetime.now(UTC)):
    fd=None
    try:
        original=_historical(authorization_file); cleanup=_historical_cleanup(cleanup_file); recon=_historical_reconciliation(cleanup_reconciliation_file); old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs); finalauth=_historical_final(continuation_finalization_file); current=_auth(recontinuation_file,clock)
        fraw=_private_file(continuation_finalization_file,32768)
        if current["continuation_finalization_authorization_sha256"]!=hashlib.sha256(fraw).hexdigest() or any(current[k]!=finalauth[k] for k in BASE) or original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}" or not docker_executable.is_absolute() or not docker_executable.is_file() or not os.access(docker_executable,os.X_OK): raise ValueError
        fbind=_final_binding(finalauth,continuation_finalization_file); fstem=hashlib.sha256(finalauth["continuation_finalization_id"].encode()).hexdigest(); fpath=evidence_directory/f"postgres-cleanup-continuation-finalization-{fstem}.json"
        if current["continuation_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(fpath,32768)).hexdigest() or _final_existing(fpath,fbind)!="later_prefix_finalized": raise ValueError
        frecord=json.loads(fpath.read_bytes(),object_pairs_hook=_pairs)
        if frecord["observed_state"]!=current["resume_from"]: raise ValueError
        cbind=_binding(original,cleanup,cleanup_file,project_name); cstem=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cstem}.claim",cbind): raise ValueError
        oldbind=_old_binding(old,cleanup_continuation_file,project_name); oldstem=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest(); oldclaim=evidence_directory/f".postgres-cleanup-continuation-{oldstem}.claim"
        if oldclaim.exists():
            _continuation_claim(oldclaim,oldbind); raise ValueError
        bind=_binding2(current,recontinuation_file,project_name); stem=hashlib.sha256(current["recontinuation_id"].encode()).hexdigest(); claim=evidence_directory/f".postgres-cleanup-recontinuation-{stem}.claim"; final=evidence_directory/f"postgres-cleanup-recontinuation-{stem}.json"; fd=_evidence_root(evidence_directory)
        if _artifact(final,bind,True):
            if claim.exists() and not _artifact(claim,bind): raise ValueError
            if claim.exists(): os.unlink(claim); os.fsync(fd)
            return _result("runtime_removed_pending_cleanup_finalization")
        if claim.exists(): raise ValueError
        a,b=_timestamp(recon["valid_from"]),_timestamp(recon["valid_until"]); raw=reconcile_disposable_postgres_cleanup(docker_executable=docker_executable,authorization_file=authorization_file,reconciliation_file=reconciliation_file,claim_reconciliation_file=claim_reconciliation_file,disposition_file=disposition_file,cleanup_file=cleanup_file,cleanup_reconciliation_file=cleanup_reconciliation_file,staging_evidence_file=staging_evidence_file,compose_file=compose_file,runtime_environment_file=runtime_environment_file,image_environment_file=image_environment_file,project_name=project_name,evidence_directory=evidence_directory,processes=processes,clock=lambda:a+(b-a)/2); obs=json.loads(raw,object_pairs_hook=_pairs)
        if set(obs)!={"schema_version","operation","outcome"} or obs["operation"]!="disposable_postgres_runtime_cleanup_reconciliation" or obs["outcome"]!=current["resume_from"]: return _result("rejected")
        started=clock().astimezone(UTC).isoformat().replace("+00:00","Z"); data=(json.dumps(dict(bind,started_at=started),sort_keys=True,separators=(",",":"))+"\n").encode(); opened=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600); os.write(opened,data); os.fsync(opened); os.close(opened); os.fsync(fd)
        runner=processes or LocalBoundedProcessRunner(); docker=str(docker_executable); nets=(bind["application_network"],bind["data_network"]); first=0 if current["resume_from"]=="container_removed" else 1
        for name in nets[first:]:
            _observe(runner,(docker,"network","rm",name),maximum=65536)
            if not _absent(_observe(runner,(docker,"network","ls","--filter",f"name=^{name}$","--format","{{.Name}}"),maximum=65536).stdout): raise ValueError
        if not _owned_volume(_observe(runner,(docker,"volume","inspect",bind["retained_volume"]),maximum=1048576).stdout,name=bind["retained_volume"],project=project_name): raise ValueError
        record=dict(bind,started_at=started,completed_at=clock().astimezone(UTC).isoformat().replace("+00:00","Z"),outcome="runtime_removed_pending_cleanup_finalization"); _write(evidence_directory,fd,final,record)
        if not _artifact(claim,bind): raise ValueError
        os.unlink(claim); os.fsync(fd); return _result("runtime_removed_pending_cleanup_finalization")
    except DisposablePostgresCleanupRecontinueUnavailable: raise
    except Exception: raise DisposablePostgresCleanupRecontinueUnavailable from None
    finally:
        if fd is not None: os.close(fd)
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-recontinue",add_help=False)
    names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--project-name",required=True)
    try:
        v=vars(p.parse_args(argv)); v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(recontinue_disposable_postgres_cleanup(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
