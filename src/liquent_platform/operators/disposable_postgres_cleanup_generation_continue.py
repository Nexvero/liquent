"""Owner-controlled generation-bound repeatable cleanup continuation."""
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
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue import CHAIN,_bind as _chain_binding,_historical_last
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue_finalize import HIST as FINAL_HIST,_authorization as _chain_final_auth,_binding4,_existing as _chain_final_existing
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root,_historical,_observe,_owned_volume,_pairs,_timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _absent,_binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT,IMAGE,OPAQUE,SHA256
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner
STEPS={"container_removed":["application_network_absent","data_network_absent"],"application_network_removed":["data_network_absent"]}
MAX_LINEAGE=16
ROOT=("chained_finalization_id",*(k for k in FINAL_HIST if k!="resume_from"),"chained_reconciliation_authorization_sha256")
LINK=("generation_continuation_id","generation","predecessor_kind","predecessor_generation",*ROOT,"predecessor_resume_from","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256","resume_from")
KEYS={"schema_version","generation_continuation_id","generation","predecessor_kind","predecessor_generation",*ROOT,"predecessor_resume_from","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256","operation","scope","resume_from","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupGenerationContinueUnavailable(Exception):
    code="disposable_postgres_cleanup_generation_continue_unavailable"
    def __init__(self):super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_):raise DisposablePostgresCleanupGenerationContinueUnavailable
def _auth(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="continue_disposable_postgres_cleanup_from_generation" or v["resume_from"] not in STEPS or v["predecessor_resume_from"] not in STEPS or type(v["generation"]) is not int or v["generation"]<1 or type(v["predecessor_generation"]) is not int or v["predecessor_kind"] not in {"lq362","repeatable_generation"} or (v["generation"]==1)!=(v["predecessor_kind"]=="lq362") or v["predecessor_generation"]!=v["generation"]-1:raise ValueError
        for k in ("generation_continuation_id","chained_finalization_id","chained_reconciliation_id","chained_continuation_id","recontinuation_finalization_id","recontinuation_reconciliation_id","recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]):raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]):raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","recontinuation_authorization_sha256","recontinuation_reconciliation_authorization_sha256","recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","chained_continuation_authorization_sha256","chained_reconciliation_authorization_sha256","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]):raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b:raise ValueError
        return v
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _historical_final(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _chain_final_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _historical_generation(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _historical_generation_final(path):
    try:
        from liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize import _authorization
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _authorization(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _bind(v,path,project):return {"schema_version":1,**{k:v[k] for k in ("generation_continuation_id","generation","predecessor_kind","predecessor_generation",*ROOT,"predecessor_resume_from","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256","scope","resume_from","executor_id","authorizer_id")},"generation_continuation_authorization_sha256":hashlib.sha256(_private_file(path,32768)).hexdigest(),"container":f"{project}-postgres-1","application_network":f"{project}-application","data_network":f"{project}-data","retained_volume":f"{project}-postgres-data","remaining_steps":STEPS[v["resume_from"]]+["data_volume_retained"]}
def _lineage(current,continuations,finalizations,chained_finalization_file,evidence_directory,project_name):
    try:
        continuations=tuple(continuations or ());finalizations=tuple(finalizations or ())
        if current["generation"]<3 or len(continuations)!=current["generation"]-1 or len(continuations)!=len(finalizations) or not 2<=len(continuations)<=MAX_LINEAGE:raise ValueError
        chain=_historical_final(chained_finalization_file);prior_final=None;prior_evidence=None;last_data=None
        from liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize import _binding5,_existing
        for number,(continuation_path,finalization_path) in enumerate(zip(continuations,finalizations),1):
            continuation=_historical_generation(continuation_path);finalization=_historical_generation_final(finalization_path)
            if continuation["generation"]!=number or finalization["generation"]!=number or any(finalization[k]!=continuation[k] for k in LINK) or finalization["generation_continuation_authorization_sha256"]!=hashlib.sha256(_private_file(continuation_path,32768)).hexdigest():raise ValueError
            if number==1:
                if continuation["predecessor_kind"]!="lq362" or continuation["predecessor_generation"]!=0 or continuation["predecessor_resume_from"]!=chain["resume_from"] or continuation["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(chained_finalization_file,32768)).hexdigest() or any(continuation[k]!=chain[k] for k in ROOT):raise ValueError
                binding=_binding4(chain,chained_finalization_file);stem=hashlib.sha256(chain["chained_finalization_id"].encode()).hexdigest();genesis=evidence_directory/f"postgres-cleanup-chained-continuation-finalization-{stem}.json";out=_chain_final_existing(genesis,binding)
                if continuation["predecessor_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(genesis,32768)).hexdigest() or out not in {"chained_continuation_attempt_finalized","later_prefix_finalized"}:raise ValueError
                if continuation["resume_from"]!=(continuation["predecessor_resume_from"] if out=="chained_continuation_attempt_finalized" else "application_network_removed"):raise ValueError
            else:
                if continuation["predecessor_kind"]!="repeatable_generation" or continuation["predecessor_generation"]!=number-1 or continuation["predecessor_resume_from"]!=prior_continuation["resume_from"] or continuation["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(prior_final_path,32768)).hexdigest() or continuation["predecessor_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(prior_evidence,32768)).hexdigest() or any(continuation[k]!=prior_final[k] for k in ROOT):raise ValueError
                if continuation["resume_from"]!=(continuation["predecessor_resume_from"] if prior_out=="generation_continuation_attempt_finalized" else "application_network_removed"):raise ValueError
            binding=_binding5(finalization,finalization_path);stem=hashlib.sha256(finalization["generation_finalization_id"].encode()).hexdigest();evidence=evidence_directory/f"postgres-cleanup-generation-continuation-finalization-{stem}.json";out=_existing(evidence,binding)
            if out not in {"generation_continuation_attempt_finalized","later_prefix_finalized"}:raise ValueError
            claim_binding=_bind(continuation,continuation_path,project_name);claim_stem=hashlib.sha256(continuation["generation_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-generation-continuation-{claim_stem}.claim"
            if claim.exists():_file(claim,claim_binding);raise ValueError
            prior_continuation,prior_final,prior_final_path,prior_evidence,prior_out=continuation,finalization,finalization_path,evidence,out;last_data=(continuation,finalization,finalization_path,evidence,out)
        previous,last,last_path,evidence,out=last_data
        if current["predecessor_generation"]!=previous["generation"] or current["predecessor_resume_from"]!=previous["resume_from"] or current["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(last_path,32768)).hexdigest() or current["predecessor_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(evidence,32768)).hexdigest() or any(current[k]!=last[k] for k in ROOT):raise ValueError
        return previous,last,evidence,out
    except DisposablePostgresCleanupGenerationContinueUnavailable:raise
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _file(path,binding,final=False):
    try:
        if not path.exists():return False
        m=path.stat(follow_symlinks=False);v=json.loads(path.read_bytes(),object_pairs_hook=_pairs);extra={"started_at","completed_at","outcome"} if final else {"started_at"}
        if not stat.S_ISREG(m.st_mode) or m.st_uid!=os.geteuid() or m.st_nlink!=1 or stat.S_IMODE(m.st_mode)!=0o600 or type(v) is not dict or set(v)!=set(binding)|extra or any(v[k]!=x for k,x in binding.items()) or (final and v["outcome"]!="runtime_removed_pending_cleanup_finalization"):raise ValueError
        return True
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
def _write(root,fd,path,record):
    temp=root/f".{path.stem}-{os.getpid()}.tmp";opened=None
    try:data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode();opened=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.write(opened,data);os.fsync(opened);os.close(opened);opened=None;os.link(temp,path);temp.unlink();os.fsync(fd);b={k:v for k,v in record.items() if k not in {"started_at","completed_at","outcome"}};assert _file(path,b,True)
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
    finally:
        if opened is not None:os.close(opened)
        try:temp.unlink()
        except FileNotFoundError:pass
def _result(outcome):return (json.dumps({"operation":"disposable_postgres_runtime_cleanup_generation_continuation","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def continue_disposable_postgres_cleanup_generation(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,recontinuation_reconciliation_file,recontinuation_finalization_file,chained_continuation_file,chained_finalization_file,generation_continuation_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,predecessor_generation_continuation_file=None,predecessor_generation_finalization_file=None,generation_lineage_continuation_files=None,generation_lineage_finalization_files=None,processes=None,clock=lambda:datetime.now(UTC)):
    fd=None
    try:
        original=_historical(authorization_file);cleanup=_historical_cleanup(cleanup_file);recon=_historical_reconciliation(cleanup_reconciliation_file);old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs);recont=_historical_recontinuation(recontinuation_file);current=_auth(generation_continuation_file,clock)
        if current["generation"]==1:
            if predecessor_generation_continuation_file is not None or predecessor_generation_finalization_file is not None or generation_lineage_continuation_files or generation_lineage_finalization_files:raise ValueError
            last=_historical_final(chained_finalization_file)
            if current["predecessor_kind"]!="lq362" or current["predecessor_resume_from"]!=last["resume_from"] or current["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(chained_finalization_file,32768)).hexdigest() or any(current[k]!=last[k] for k in ROOT):raise ValueError
            lb=_binding4(last,chained_finalization_file);ls=hashlib.sha256(last["chained_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-chained-continuation-finalization-{ls}.json";out=_chain_final_existing(lp,lb);allowed={"chained_continuation_attempt_finalized","later_prefix_finalized"};attempt="chained_continuation_attempt_finalized"
        elif current["generation"]==2:
            if current["predecessor_kind"]!="repeatable_generation" or predecessor_generation_continuation_file is None or predecessor_generation_finalization_file is None or generation_lineage_continuation_files or generation_lineage_finalization_files:raise ValueError
            previous=_historical_generation(predecessor_generation_continuation_file);last=_historical_generation_final(predecessor_generation_finalization_file)
            if previous["generation"]!=1 or last["generation"]!=1 or current["predecessor_generation"]!=1 or current["predecessor_resume_from"]!=previous["resume_from"] or current["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(predecessor_generation_finalization_file,32768)).hexdigest() or any(current[k]!=last[k] for k in ROOT):raise ValueError
            from liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize import _binding5,_existing
            lb=_binding5(last,predecessor_generation_finalization_file);ls=hashlib.sha256(last["generation_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-generation-continuation-finalization-{ls}.json";out=_existing(lp,lb);allowed={"generation_continuation_attempt_finalized","later_prefix_finalized"};attempt="generation_continuation_attempt_finalized"
            pb=_bind(previous,predecessor_generation_continuation_file,project_name);ps=hashlib.sha256(previous["generation_continuation_id"].encode()).hexdigest();pc=evidence_directory/f".postgres-cleanup-generation-continuation-{ps}.claim"
            if pc.exists():_file(pc,pb);raise ValueError
        else:
            if current["predecessor_kind"]!="repeatable_generation" or predecessor_generation_continuation_file is not None or predecessor_generation_finalization_file is not None:raise ValueError
            previous,last,lp,out=_lineage(current,generation_lineage_continuation_files,generation_lineage_finalization_files,chained_finalization_file,evidence_directory,project_name);allowed={"generation_continuation_attempt_finalized","later_prefix_finalized"};attempt="generation_continuation_attempt_finalized"
        if original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}" or not docker_executable.is_absolute() or not docker_executable.is_file() or not os.access(docker_executable,os.X_OK):raise ValueError
        if current["predecessor_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(lp,32768)).hexdigest() or out not in allowed:raise ValueError
        expected=current["predecessor_resume_from"] if out==attempt else "application_network_removed"
        if current["resume_from"]!=expected:raise ValueError
        cbind=_binding(original,cleanup,cleanup_file,project_name);cs=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cs}.claim",cbind):raise ValueError
        ob=_old_binding(old,cleanup_continuation_file,project_name);osx=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest();oc=evidence_directory/f".postgres-cleanup-continuation-{osx}.claim"
        if oc.exists():_continuation_claim(oc,ob);raise ValueError
        rb=_binding2(recont,recontinuation_file,project_name);rs=hashlib.sha256(recont["recontinuation_id"].encode()).hexdigest();rc=evidence_directory/f".postgres-cleanup-recontinuation-{rs}.claim"
        if rc.exists():_artifact(rc,rb);raise ValueError
        bind=_bind(current,generation_continuation_file,project_name);stem=hashlib.sha256(current["generation_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-generation-continuation-{stem}.claim";final=evidence_directory/f"postgres-cleanup-generation-continuation-{stem}.json";fd=_evidence_root(evidence_directory)
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
    except DisposablePostgresCleanupGenerationContinueUnavailable:raise
    except Exception:raise DisposablePostgresCleanupGenerationContinueUnavailable from None
    finally:
        if fd is not None:os.close(fd)
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-generation-continue",add_help=False);names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","recontinuation-reconciliation-file","recontinuation-finalization-file","chained-continuation-file","chained-finalization-file","generation-continuation-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--predecessor-generation-continuation-file",type=Path);p.add_argument("--predecessor-generation-finalization-file",type=Path);p.add_argument("--generation-lineage-continuation-file",dest="generation_lineage_continuation_files",action="append",type=Path);p.add_argument("--generation-lineage-finalization-file",dest="generation_lineage_finalization_files",action="append",type=Path)
    p.add_argument("--project-name",required=True)
    try:v=vars(p.parse_args(argv));v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(continue_disposable_postgres_cleanup_generation(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
