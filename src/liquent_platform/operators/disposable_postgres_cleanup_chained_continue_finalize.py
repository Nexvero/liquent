"""Evidence-first finalization of a reconciled chained cleanup continuation."""
from __future__ import annotations
import argparse,hashlib,json,os,stat,sys
from datetime import UTC,datetime,timedelta
from pathlib import Path
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue import _auth as _chain_auth,_bind,_file
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue_reconcile import COMPARE,_authorization as _reconcile_auth,_historical_chain,reconcile_disposable_postgres_cleanup_chained_continuation
from liquent_platform.operators.disposable_postgres_cleanup_continue import _continuation_claim,_evidence_binding as _old_binding
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import _claim,_historical_cleanup
from liquent_platform.operators.disposable_postgres_cleanup_recontinue import _artifact,_binding2
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_reconcile import _historical_recontinuation
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root,_historical,_pairs,_timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT,IMAGE,OPAQUE,SHA256

FINAL={"chained_continuation_evidence_present":"chained_continuation_evidence_confirmed","chained_continuation_not_started":"chained_continuation_attempt_finalized","application_network_removed":"later_prefix_finalized","runtime_removed_evidence_missing":"runtime_removal_ready_for_cleanup_finalization"}
HIST=("chained_reconciliation_id",*COMPARE,"chained_continuation_authorization_sha256")
KEYS={"schema_version","chained_finalization_id",*HIST,"chained_reconciliation_authorization_sha256","operation","scope","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupChainedContinueFinalizeUnavailable(Exception):
    code="disposable_postgres_cleanup_chained_continue_finalize_unavailable"
    def __init__(self):super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_):raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable
def _authorization(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="finalize_disposable_postgres_cleanup_chained_continuation" or v["resume_from"] not in {"container_removed","application_network_removed"} or v["previous_resume_from"] not in {"container_removed","application_network_removed"}:raise ValueError
        for k in ("chained_finalization_id","chained_reconciliation_id","chained_continuation_id","recontinuation_finalization_id","recontinuation_reconciliation_id","recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]):raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]):raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","recontinuation_authorization_sha256","recontinuation_reconciliation_authorization_sha256","recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","chained_continuation_authorization_sha256","chained_reconciliation_authorization_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]):raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b:raise ValueError
        return v
    except Exception:raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable from None
def _historical_reconciliation(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _reconcile_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable from None
def _binding4(v,path):return {"schema_version":1,**{k:v[k] for k in ("chained_finalization_id",*HIST,"scope","executor_id","authorizer_id")},"finalization_authorization_sha256":hashlib.sha256(_private_file(path,32768)).hexdigest()}
def _existing(path,binding):
    try:
        if not path.exists():return None
        m=path.stat(follow_symlinks=False);v=json.loads(path.read_bytes(),object_pairs_hook=_pairs)
        if not stat.S_ISREG(m.st_mode) or m.st_uid!=os.geteuid() or m.st_nlink!=1 or stat.S_IMODE(m.st_mode)!=0o600 or type(v) is not dict or set(v)!=set(binding)|{"observed_state","outcome","started_at","completed_at"} or any(v[k]!=x for k,x in binding.items()) or v["observed_state"] not in FINAL or v["outcome"]!=FINAL[v["observed_state"]]:raise ValueError
        for k in ("started_at","completed_at"):
            if datetime.fromisoformat(v[k].replace("Z","+00:00")).tzinfo is None:raise ValueError
        return v["outcome"]
    except Exception:raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable from None
def _write(root,fd,path,record):
    temp=root/f".{path.stem}-{os.getpid()}.tmp";opened=None
    try:
        data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode();opened=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.write(opened,data);os.fsync(opened);os.close(opened);opened=None;os.link(temp,path);temp.unlink();os.fsync(fd);binding={k:v for k,v in record.items() if k not in {"observed_state","outcome","started_at","completed_at"}}
        if _existing(path,binding)!=record["outcome"]:raise ValueError
    except Exception:raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable from None
    finally:
        if opened is not None:os.close(opened)
        try:temp.unlink()
        except FileNotFoundError:pass
def _result(outcome):return (json.dumps({"operation":"disposable_postgres_cleanup_chained_continuation_finalization","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def finalize_disposable_postgres_cleanup_chained_continuation(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,recontinuation_reconciliation_file,recontinuation_finalization_file,chained_continuation_file,chained_reconciliation_file,chained_finalization_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,processes=None,clock=lambda:datetime.now(UTC)):
    fd=None
    try:
        original=_historical(authorization_file);cleanup=_historical_cleanup(cleanup_file);old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs);recont=_historical_recontinuation(recontinuation_file);chain=_historical_chain(chained_continuation_file);recon=_historical_reconciliation(chained_reconciliation_file);current=_authorization(chained_finalization_file,clock)
        if current["chained_reconciliation_authorization_sha256"]!=hashlib.sha256(_private_file(chained_reconciliation_file,32768)).hexdigest() or any(current[k]!=recon[k] for k in HIST) or original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}":raise ValueError
        cb=_binding(original,cleanup,cleanup_file,project_name);cs=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cs}.claim",cb):return _result("investigation_required")
        ob=_old_binding(old,cleanup_continuation_file,project_name);osx=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest();oc=evidence_directory/f".postgres-cleanup-continuation-{osx}.claim"
        if oc.exists():_continuation_claim(oc,ob);raise ValueError
        rb=_binding2(recont,recontinuation_file,project_name);rs=hashlib.sha256(recont["recontinuation_id"].encode()).hexdigest();rc=evidence_directory/f".postgres-cleanup-recontinuation-{rs}.claim"
        if rc.exists():_artifact(rc,rb);raise ValueError
        bind=_bind(chain,chained_continuation_file,project_name);stem=hashlib.sha256(chain["chained_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-chained-continuation-{stem}.claim";fb=_binding4(current,chained_finalization_file);fs=hashlib.sha256(current["chained_finalization_id"].encode()).hexdigest();final=evidence_directory/f"postgres-cleanup-chained-continuation-finalization-{fs}.json";fd=_evidence_root(evidence_directory);existing=_existing(final,fb)
        if existing:
            if claim.exists() and not _file(claim,bind):raise ValueError
            if claim.exists():os.unlink(claim);os.fsync(fd)
            return _result(existing)
        a,b=_timestamp(recon["valid_from"]),_timestamp(recon["valid_until"]);raw=reconcile_disposable_postgres_cleanup_chained_continuation(docker_executable=docker_executable,authorization_file=authorization_file,reconciliation_file=reconciliation_file,claim_reconciliation_file=claim_reconciliation_file,disposition_file=disposition_file,cleanup_file=cleanup_file,cleanup_reconciliation_file=cleanup_reconciliation_file,cleanup_continuation_file=cleanup_continuation_file,continuation_reconciliation_file=continuation_reconciliation_file,continuation_finalization_file=continuation_finalization_file,recontinuation_file=recontinuation_file,recontinuation_reconciliation_file=recontinuation_reconciliation_file,recontinuation_finalization_file=recontinuation_finalization_file,chained_continuation_file=chained_continuation_file,chained_reconciliation_file=chained_reconciliation_file,staging_evidence_file=staging_evidence_file,compose_file=compose_file,runtime_environment_file=runtime_environment_file,image_environment_file=image_environment_file,project_name=project_name,evidence_directory=evidence_directory,processes=processes,clock=lambda:a+(b-a)/2);obs=json.loads(raw,object_pairs_hook=_pairs)
        if type(obs) is not dict or set(obs)!={"schema_version","operation","outcome"} or obs["schema_version"]!=1 or obs["operation"]!="disposable_postgres_cleanup_chained_continuation_reconciliation":raise ValueError
        state=obs["outcome"]
        if state=="not_found":return _result("not_found")
        if state=="conflict":return _result("investigation_required")
        if state not in FINAL:raise ValueError
        outcome=FINAL[state];started=clock().astimezone(UTC).isoformat().replace("+00:00","Z");_write(evidence_directory,fd,final,dict(fb,observed_state=state,outcome=outcome,started_at=started,completed_at=clock().astimezone(UTC).isoformat().replace("+00:00","Z")))
        if claim.exists() and not _file(claim,bind):raise ValueError
        if claim.exists():os.unlink(claim);os.fsync(fd)
        return _result(outcome)
    except DisposablePostgresCleanupChainedContinueFinalizeUnavailable:raise
    except Exception:raise DisposablePostgresCleanupChainedContinueFinalizeUnavailable from None
    finally:
        if fd is not None:os.close(fd)
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-chain-finalize",add_help=False);names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","recontinuation-reconciliation-file","recontinuation-finalization-file","chained-continuation-file","chained-reconciliation-file","chained-finalization-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--project-name",required=True)
    try:v=vars(p.parse_args(argv));v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(finalize_disposable_postgres_cleanup_chained_continuation(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
