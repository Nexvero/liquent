"""Bounded argv process execution and neutral staging phase reduction."""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from liquent_platform.operators.research_worker_staging_executor import PHASES


FACT_KEYS = {
    "image_digest": "digest_matches", "image_revision": "revision_matches",
    "entrypoint": "entrypoint_present", "runtime_identity": "uid_gid_matches",
    "disposable_postgres": "database_isolated", "rollback": "rollback_current",
    "trading_disabled": "trading_disabled", "compose_render": "render_valid",
    "command": "command_exact", "networks": "networks_isolated",
    "mounts": "mounts_bounded", "secret_mount": "secret_owner_only",
    "grace": "grace_bounded", "input_ownership": "inputs_owner_only",
    "data_read_only": "data_read_only",
    "artifact_capabilities": "artifact_capabilities_valid",
    "migration_gate": "migration_gate_succeeded",
    "migration_head": "migration_head_exact", "idle_start": "idle_stable",
    "idle_no_mutation": "idle_mutation_free", "log_redaction": "logs_redacted",
    "authorized_acceptance": "acceptance_authorized",
    "claim_heartbeat": "claim_heartbeat_exact",
    "terminal_outcome": "terminal_outcome_exact",
    "artifact_integrity": "artifact_hash_matches",
    "revocation": "revocation_fail_closed", "idle_sigterm": "idle_stop_clean",
    "running_sigterm": "running_stop_bounded", "no_sigkill": "sigkill_unused",
}
FORBIDDEN = re.compile(
    rb"(?:postgres(?:ql)?(?:\+psycopg)?://|https?://|/Users/|/home/|/run/secrets/|"
    rb"-----BEGIN|authorization|password|credential|database_url)", re.IGNORECASE,
)


class StagingProcessUnavailable(Exception):
    code = "staging_process_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    truncated: bool
    hard_killed: bool

    def __repr__(self) -> str:
        return "ProcessObservation()"


@dataclass(frozen=True, slots=True)
class ReducedPhaseOutput:
    phase: str
    status: str
    content: bytes

    def __repr__(self) -> str:
        return "ReducedPhaseOutput()"


class LocalBoundedProcessRunner:
    """Execute one explicit argv with bounded nonblocking byte capture."""

    __slots__ = ("_monotonic",)

    def __init__(self, *, monotonic=time.monotonic) -> None:
        self._monotonic = monotonic

    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        environment: dict[str, str],
        timeout_seconds: float,
        maximum_output_bytes: int,
        terminate_grace_seconds: float = 1.0,
    ) -> ProcessObservation:
        process = None
        selector = selectors.DefaultSelector()
        output = {"stdout": bytearray(), "stderr": bytearray()}
        timed_out = truncated = hard_killed = False
        try:
            self._validate(argv, cwd, environment, timeout_seconds,
                           maximum_output_bytes, terminate_grace_seconds)
            process = subprocess.Popen(
                list(argv), cwd=cwd, env=dict(environment), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                start_new_session=True,
            )
            assert process.stdout is not None and process.stderr is not None
            for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            deadline = self._monotonic() + timeout_seconds
            while selector.get_map() or process.poll() is None:
                remaining = deadline - self._monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    target = output[key.data]
                    available = maximum_output_bytes - len(target)
                    if len(chunk) > available:
                        target.extend(chunk[:max(0, available)])
                        truncated = True
                        break
                    target.extend(chunk)
                if truncated:
                    break
            if timed_out or truncated:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=terminate_grace_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    hard_killed = True
            process.wait()
            return ProcessObservation(
                process.returncode, bytes(output["stdout"]), bytes(output["stderr"]),
                timed_out, truncated, hard_killed,
            )
        except StagingProcessUnavailable:
            raise
        except Exception:
            raise StagingProcessUnavailable from None
        finally:
            selector.close()
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()

    @staticmethod
    def _validate(argv, cwd, environment, timeout, maximum, grace) -> None:
        if (
            type(argv) is not tuple or not argv
            or any(type(item) is not str or not item or "\0" in item for item in argv)
            or not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file()
            or not isinstance(cwd, Path) or not cwd.is_absolute() or not cwd.is_dir()
            or type(environment) is not dict
            or any(type(key) is not str or type(value) is not str or "\0" in key + value
                   for key, value in environment.items())
            or type(timeout) not in (int, float) or not 0 < timeout <= 3600
            or type(grace) not in (int, float) or not 0 < grace <= 30
            or type(maximum) is not int or not 1 <= maximum <= 1_048_576
        ):
            raise StagingProcessUnavailable


def reduce_phase_output(phase: str, observation: ProcessObservation) -> ReducedPhaseOutput:
    """Reduce one successful bounded process result to one neutral fact."""

    try:
        if phase not in PHASES or type(observation) is not ProcessObservation:
            raise StagingProcessUnavailable
        if (
            observation.returncode != 0 or observation.timed_out
            or observation.truncated or observation.hard_killed
            or observation.stderr or not observation.stdout
            or FORBIDDEN.search(observation.stdout)
        ):
            raise StagingProcessUnavailable

        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise StagingProcessUnavailable
                result[key] = value
            return result

        value = json.loads(observation.stdout, object_pairs_hook=pairs)
        if type(value) is not dict or set(value) != {"schema_version", "phase", "facts"}:
            raise StagingProcessUnavailable
        if value["schema_version"] != 1 or value["phase"] != phase:
            raise StagingProcessUnavailable
        facts = value["facts"]
        fact = FACT_KEYS[phase]
        if type(facts) is not dict or set(facts) != {fact} or type(facts[fact]) is not bool:
            raise StagingProcessUnavailable
        status = "passed" if facts[fact] else "failed"
        content = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return ReducedPhaseOutput(phase, status, content)
    except StagingProcessUnavailable:
        raise
    except Exception:
        raise StagingProcessUnavailable from None
