"""Fixed-operation-root one-shot and read-only audit CLI."""
import argparse
import math
import unicodedata
from dataclasses import dataclass,field,replace
from datetime import datetime
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import ManifestHandoffSupervisorEngineApiStagingRunAcceptance,ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation,build_staging_run_acceptance,observe_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import ManifestHandoffSupervisorEngineApiStagingRunAuthority,decode_staging_run_authority
from tools import engine_api_joint_staging_acceptance_audit as audit_clock
from tools import engine_api_joint_staging_one_shot_verify as one_shot_clock
from tools.engine_api_joint_staging_acceptance_audit import inspect_registry,observe_registry,verify_accepted_current
from tools.engine_api_joint_staging_one_shot_verify import verify_and_accept
from tools.engine_api_joint_staging_operation_root import JointEngineApiStagingOperationRoots,resolve_operation_root,validate_operation_roots
from tools.engine_api_joint_staging_policy_verify import _monotonic_now
from tools.engine_api_joint_staging_provenance_snapshot import verify_run_bound_snapshot
from tools.engine_api_joint_staging_source_set import JointEngineApiRunBoundSourceObservation,observe_run_bound_source_set

_NATIVE_PATH_TYPE=type(Path())
_MAX_CLI_ROOT_BYTES=4095
_MAX_CLI_ROOT_COMPONENT_BYTES=255

class _DetailFreeArgumentParser(argparse.ArgumentParser):
    def error(self,message): raise ManifestHandoffRegistryUnavailable
    def exit(self,status=0,message=None): raise ManifestHandoffRegistryUnavailable

class _SingleValueAction(argparse.Action):
    def __call__(self,parser,namespace,values,option_string=None):
        if getattr(namespace,self.dest,None) is not None: raise ManifestHandoffRegistryUnavailable
        setattr(namespace,self.dest,values)

def _validate_result_observations(values):
    if type(values)is not tuple or any(type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation for value in values): raise ManifestHandoffRegistryUnavailable
    run_ids=tuple(value.acceptance.run_id for value in values);identities=tuple(value.marker_identity for value in values);states=tuple(value.marker_state for value in values)
    if run_ids!=tuple(sorted(run_ids)) or len(set(run_ids))!=len(run_ids) or len(set(identities))!=len(identities) or len(set(states))!=len(states): raise ManifestHandoffRegistryUnavailable

def _validate_result_values(values):
    if type(values)is not tuple or any(type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance for value in values): raise ManifestHandoffRegistryUnavailable

def _observe_validated_registry(root,*,expected_acceptance_identity):
    values=observe_registry(root,expected_acceptance_identity=expected_acceptance_identity);_validate_result_observations(values);return values

def _inspect_validated_registry(root,*,expected_acceptance_identity):
    values=inspect_registry(root,expected_acceptance_identity=expected_acceptance_identity);_validate_result_values(values);return values

def _observe_validated_source(root,*,expected_root_identity):
    value=observe_run_bound_source_set(root,expected_root_identity=expected_root_identity)
    if type(value)is not JointEngineApiRunBoundSourceObservation: raise ManifestHandoffRegistryUnavailable
    return value

def _observe_validated_acceptance(root,run_id,*,expected_root_identity):
    value=observe_staging_run_acceptance(root,run_id,expected_root_identity=expected_root_identity)
    if type(value)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation: raise ManifestHandoffRegistryUnavailable
    return value

def _resolve_validated_operation_root(root):
    value=resolve_operation_root(root)
    if type(value)is not JointEngineApiStagingOperationRoots: raise ManifestHandoffRegistryUnavailable
    return value

def _validate_operation_root_completion(root,expected,*,allow_acceptance_state_change=False):
    result=validate_operation_roots(root,expected,allow_acceptance_state_change=True) if allow_acceptance_state_change else validate_operation_roots(root,expected)
    if result is not None: raise ManifestHandoffRegistryUnavailable

def _verify_snapshot_completion(snapshot,*,now):
    if verify_run_bound_snapshot(snapshot,now=now) is not None: raise ManifestHandoffRegistryUnavailable

def _derive_source_acceptance(source):
    if type(source)is not JointEngineApiRunBoundSourceObservation: raise ManifestHandoffRegistryUnavailable
    authority=decode_staging_run_authority(source.snapshot.run_authority)
    if type(authority)is not ManifestHandoffSupervisorEngineApiStagingRunAuthority: raise ManifestHandoffRegistryUnavailable
    expected=build_staging_run_acceptance(authority,source.snapshot.run_envelope)
    if type(expected)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptance: raise ManifestHandoffRegistryUnavailable
    return authority,expected

def _validate_utc(value):
    if type(value)is not datetime or value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds()!=0: raise ManifestHandoffRegistryUnavailable
    return value

def _run_detail_free(operation):
    try: return operation()
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def _run_completed_detail_free(operation):
    result=_run_detail_free(operation)
    if result is not None: raise ManifestHandoffRegistryUnavailable

def _validate_root_text(value):
    if type(value)is not str: raise ManifestHandoffRegistryUnavailable
    try: encoded=value.encode("utf-8")
    except UnicodeError: raise ManifestHandoffRegistryUnavailable from None
    components=value.split("/")[1:]
    if len(encoded)>_MAX_CLI_ROOT_BYTES or unicodedata.normalize("NFC",value)!=value or any(unicodedata.category(character) in ("Cc","Cf","Cs") for character in value): raise ManifestHandoffRegistryUnavailable
    if not value.startswith("/") or value=="/" or value.endswith("/") or any(component in ("",".","..") or len(component.encode("utf-8"))>_MAX_CLI_ROOT_COMPONENT_BYTES for component in components): raise ManifestHandoffRegistryUnavailable
    return value

def _validate_direct_root(root):
    if type(root)is not _NATIVE_PATH_TYPE: raise ManifestHandoffRegistryUnavailable
    _validate_root_text(str(root))
    if not root.is_absolute() or root.anchor!="/" or root==Path("/") or ".." in root.parts: raise ManifestHandoffRegistryUnavailable
    return root

def _parse_cli_root(value):
    _validate_root_text(value)
    return _validate_direct_root(Path(value))

def _read_validated_clock(reader,validator): return _run_detail_free(lambda:validator(reader()))

def _accept_utc_now(): return _read_validated_clock(one_shot_clock._utc_now,_validate_utc)
def _audit_utc_now(): return _read_validated_clock(audit_clock._utc_now,_validate_utc)

def _validate_monotonic(value):
    if type(value)is not float or not math.isfinite(value) or value<0: raise ManifestHandoffRegistryUnavailable
    return value

def _outer_monotonic_now(): return _read_validated_clock(_monotonic_now,_validate_monotonic)

@dataclass(frozen=True,slots=True)
class JointEngineApiRegistryAuditResult:
    values:tuple
    observations:tuple
    def __post_init__(self):
        _validate_result_values(self.values)
        _validate_result_observations(self.observations)
        if tuple(value.acceptance for value in self.observations)!=self.values: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiRegistryAuditResult()"

@dataclass(frozen=True,slots=True)
class JointEngineApiAcceptedAuditResult:
    source:JointEngineApiRunBoundSourceObservation
    marker:ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation
    registry:tuple
    def __post_init__(self):
        _validate_result_observations(self.registry)
        if type(self.source)is not JointEngineApiRunBoundSourceObservation or type(self.marker)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation: raise ManifestHandoffRegistryUnavailable
        _,expected=_derive_source_acceptance(self.source)
        if self.marker.acceptance!=expected or sum(value==self.marker for value in self.registry)!=1: raise ManifestHandoffRegistryUnavailable
    def __repr__(self): return "JointEngineApiAcceptedAuditResult()"

@dataclass(frozen=True,slots=True)
class JointEngineApiAcceptResult:
    source:JointEngineApiRunBoundSourceObservation
    registry:tuple
    created:ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation=field(init=False)
    def __post_init__(self):
        _validate_result_observations(self.registry)
        if type(self.source)is not JointEngineApiRunBoundSourceObservation: raise ManifestHandoffRegistryUnavailable
        _,expected=_derive_source_acceptance(self.source)
        matches=tuple(value for value in self.registry if value.acceptance==expected)
        if len(matches)!=1: raise ManifestHandoffRegistryUnavailable
        object.__setattr__(self,"created",matches[0])
    def __repr__(self): return "JointEngineApiAcceptResult()"

def _within_operation_roots(root:Path,operation,*,allow_acceptance_state_change:bool=False,success_check=None):
    resolved=_resolve_validated_operation_root(root)
    completed=False;expected=resolved
    try:
        result=operation(resolved)
        if allow_acceptance_state_change:
            current=_resolve_validated_operation_root(root);expected=replace(resolved,acceptance_state=current.acceptance_state)
            if current!=expected: raise ManifestHandoffRegistryUnavailable
            if success_check is not None: success_check(current,result)
        elif success_check is not None:
            current=_resolve_validated_operation_root(root)
            if current!=resolved: raise ManifestHandoffRegistryUnavailable
            success_check(current,result)
        completed=True
        return result
    finally:
        if allow_acceptance_state_change and not completed: _validate_operation_root_completion(root,resolved,allow_acceptance_state_change=True)
        elif allow_acceptance_state_change: _validate_operation_root_completion(root,expected)
        else: _validate_operation_root_completion(root,resolved)

def _accept_once(root:Path)->None:
    initial_now=_accept_utc_now();initial_monotonic=_outer_monotonic_now()
    def operation(resolved):
        source=_observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity);authority,expected=_derive_source_acceptance(source)
        before=_observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)
        created=verify_and_accept(resolved.source_root,resolved.acceptance_root,expected_source_identity=resolved.source_identity,expected_acceptance_identity=resolved.acceptance_identity)
        if type(created)is not ManifestHandoffSupervisorEngineApiStagingRunAcceptanceObservation: raise ManifestHandoffRegistryUnavailable
        after=_observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)
        added=tuple(value for value in after if value not in before)
        if len(after)!=len(before)+1 or any(value not in after for value in before) or added!=(created,) or created.acceptance!=expected: raise ManifestHandoffRegistryUnavailable
        result=JointEngineApiAcceptResult(source,after)
        if result.created!=created: raise ManifestHandoffRegistryUnavailable
        return result
    def success_check(resolved,result):
        if type(result)is not JointEngineApiAcceptResult: raise ManifestHandoffRegistryUnavailable
        source,registry,created=result.source,result.registry,result.created
        if _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=registry: raise ManifestHandoffRegistryUnavailable
        if _observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity)!=source: raise ManifestHandoffRegistryUnavailable
        verification_now=_accept_utc_now()
        if verification_now<initial_now: raise ManifestHandoffRegistryUnavailable
        _verify_snapshot_completion(source.snapshot,now=verification_now)
        if _observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity)!=source: raise ManifestHandoffRegistryUnavailable
        final_monotonic=_outer_monotonic_now();final_now=_accept_utc_now()
        if final_now<verification_now or final_monotonic<initial_monotonic or final_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
        _verify_snapshot_completion(source.snapshot,now=final_now)
        if _observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity)!=source: raise ManifestHandoffRegistryUnavailable
        authority,_=_derive_source_acceptance(source)
        if _observe_validated_acceptance(resolved.acceptance_root,authority.run_id,expected_root_identity=resolved.acceptance_identity)!=created: raise ManifestHandoffRegistryUnavailable
        if _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=registry: raise ManifestHandoffRegistryUnavailable
        terminal_monotonic=_outer_monotonic_now()
        if terminal_monotonic<final_monotonic or terminal_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
    _within_operation_roots(root,operation,allow_acceptance_state_change=True,success_check=success_check)

def accept_once(root:Path)->None: return _run_completed_detail_free(lambda:_accept_once(_validate_direct_root(root)))

def _audit(root:Path,*,accepted_source:bool)->None:
    if type(accepted_source)is not bool: raise ManifestHandoffRegistryUnavailable
    initial_now=_audit_utc_now() if accepted_source else None;initial_monotonic=_outer_monotonic_now()
    def operation(resolved):
        if accepted_source:
            evidence=verify_accepted_current(resolved.source_root,resolved.acceptance_root,expected_source_identity=resolved.source_identity,expected_acceptance_identity=resolved.acceptance_identity)
            if type(evidence)is not tuple or len(evidence)!=2: raise ManifestHandoffRegistryUnavailable
            return JointEngineApiAcceptedAuditResult(*evidence,_observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity))
        values=_inspect_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity);return JointEngineApiRegistryAuditResult(values,_observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity))
    def success_check(resolved,result):
        expected_type=JointEngineApiAcceptedAuditResult if accepted_source else JointEngineApiRegistryAuditResult
        if type(result)is not expected_type: raise ManifestHandoffRegistryUnavailable
        if type(result)is JointEngineApiRegistryAuditResult:
            if _inspect_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=result.values or _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=result.observations: raise ManifestHandoffRegistryUnavailable
        elif type(result)is JointEngineApiAcceptedAuditResult:
            source,marker,registry=result.source,result.marker,result.registry
            if _observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity)!=source: raise ManifestHandoffRegistryUnavailable
            authority,_=_derive_source_acceptance(source)
            if _observe_validated_acceptance(resolved.acceptance_root,authority.run_id,expected_root_identity=resolved.acceptance_identity)!=marker or _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=registry: raise ManifestHandoffRegistryUnavailable
        else: raise ManifestHandoffRegistryUnavailable
        final_monotonic=_outer_monotonic_now()
        if final_monotonic<initial_monotonic or final_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
        if type(result)is JointEngineApiRegistryAuditResult:
            if _inspect_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=result.values or _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=result.observations: raise ManifestHandoffRegistryUnavailable
            terminal_monotonic=_outer_monotonic_now()
            if terminal_monotonic<final_monotonic or terminal_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
        elif type(result)is JointEngineApiAcceptedAuditResult:
            final_now=_audit_utc_now()
            if final_now<initial_now: raise ManifestHandoffRegistryUnavailable
            source,marker,registry=result.source,result.marker,result.registry;_verify_snapshot_completion(source.snapshot,now=final_now)
            if _observe_validated_source(resolved.source_root,expected_root_identity=resolved.source_identity)!=source: raise ManifestHandoffRegistryUnavailable
            authority,_=_derive_source_acceptance(source)
            if _observe_validated_acceptance(resolved.acceptance_root,authority.run_id,expected_root_identity=resolved.acceptance_identity)!=marker or _observe_validated_registry(resolved.acceptance_root,expected_acceptance_identity=resolved.acceptance_identity)!=registry: raise ManifestHandoffRegistryUnavailable
            terminal_monotonic=_outer_monotonic_now()
            if terminal_monotonic<final_monotonic or terminal_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
    _within_operation_roots(root,operation,success_check=success_check)

def audit(root:Path,*,accepted_source:bool)->None:
    def operation():
        if type(accepted_source)is not bool: raise ManifestHandoffRegistryUnavailable
        return _audit(_validate_direct_root(root),accepted_source=accepted_source)
    return _run_completed_detail_free(operation)

def _dispatch_cli(root,mode):
    if type(mode)is not str or mode not in ("accept-once","audit-registry","audit-accepted-source"): raise ManifestHandoffRegistryUnavailable
    if mode=="accept-once": result=accept_once(root)
    else: result=audit(root,accepted_source=mode=="audit-accepted-source")
    if result is not None: raise ManifestHandoffRegistryUnavailable

def _validate_cli_namespace(value):
    if type(value)is not argparse.Namespace or set(vars(value))!={"operation_root","mode"}: raise ManifestHandoffRegistryUnavailable
    root=value.operation_root;mode=value.mode
    if type(root)is not _NATIVE_PATH_TYPE or type(mode)is not str or mode not in ("accept-once","audit-registry","audit-accepted-source"): raise ManifestHandoffRegistryUnavailable
    return root,mode

def main(argv=None)->int:
    try:
        parser=_DetailFreeArgumentParser(add_help=False,allow_abbrev=False);parser.add_argument("--operation-root",required=True,type=_parse_cli_root,action=_SingleValueAction);parser.add_argument("--mode",required=True,choices=("accept-once","audit-registry","audit-accepted-source"),action=_SingleValueAction)
        root,mode=_validate_cli_namespace(parser.parse_args(argv))
        if _dispatch_cli(root,mode) is not None: raise ManifestHandoffRegistryUnavailable
        return 0
    except (BaseException,): return 2

if __name__=="__main__": raise SystemExit(main())
