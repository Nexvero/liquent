"""Fixed staging phase commands and private neutral evidence object storage."""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from liquent_platform.operators.research_worker_staging_executor import (
    PHASES, StagingPhaseEvidence, StagingRunAuthorization,
)
from liquent_platform.operators.staging_process_adapter import (
    LocalBoundedProcessRunner, ProcessObservation, ReducedPhaseOutput,
    StagingProcessUnavailable, reduce_phase_output,
)


_READ_ONLY = frozenset(PHASES[:4] + PHASES[6:16] + PHASES[17:21] + PHASES[24:25] + PHASES[28:])


class StagingPhaseCompositionUnavailable(Exception):
    code = "staging_phase_composition_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class StagingProcessInputs:
    probe_executable: Path
    docker_executable: Path
    working_directory: Path
    authorization_file: Path
    compose_file: Path
    runtime_environment_file: Path
    image_environment_file: Path

    def __post_init__(self) -> None:
        for value in (
            self.probe_executable, self.docker_executable, self.working_directory,
            self.authorization_file, self.compose_file, self.runtime_environment_file,
            self.image_environment_file,
        ):
            if not isinstance(value, Path) or not value.is_absolute():
                raise ValueError("staging process paths must be absolute")

    def __repr__(self) -> str:
        return "StagingProcessInputs()"


@dataclass(frozen=True, slots=True)
class StagingProcessRequest:
    argv: tuple[str, ...]
    cwd: Path
    environment: dict[str, str]
    timeout_seconds: float
    maximum_output_bytes: int
    terminate_grace_seconds: float

    def __repr__(self) -> str:
        return "StagingProcessRequest()"


class BoundedProcessRunner(Protocol):
    def run(self, argv: tuple[str, ...], **kwargs) -> ProcessObservation: ...


class FixedStagingPhaseCommands:
    __slots__ = ("_inputs",)

    def __init__(self, inputs: StagingProcessInputs) -> None:
        if type(inputs) is not StagingProcessInputs:
            raise ValueError("staging process inputs are required")
        self._inputs = inputs

    def __repr__(self) -> str:
        return "FixedStagingPhaseCommands()"

    def request(self, phase: str, authorization: StagingRunAuthorization) -> StagingProcessRequest:
        try:
            if phase not in PHASES or type(authorization) is not StagingRunAuthorization:
                raise StagingPhaseCompositionUnavailable
            self._validate_inputs()
            project = f"liquent-{authorization.run_id}"
            if len(project) > 63:
                raise StagingPhaseCompositionUnavailable
            argv = (
                str(self._inputs.probe_executable), "--phase", phase,
                "--docker-executable", str(self._inputs.docker_executable),
                "--authorization-file", str(self._inputs.authorization_file),
                "--compose-file", str(self._inputs.compose_file),
                "--runtime-env-file", str(self._inputs.runtime_environment_file),
                "--image-env-file", str(self._inputs.image_environment_file),
                "--project-name", project,
            )
            return StagingProcessRequest(
                argv, self._inputs.working_directory,
                {"LANG": "C", "LC_ALL": "C"},
                60.0 if phase in _READ_ONLY else 300.0,
                65_536, 5.0,
            )
        except StagingPhaseCompositionUnavailable:
            raise
        except Exception:
            raise StagingPhaseCompositionUnavailable from None

    def _validate_inputs(self) -> None:
        for path in (self._inputs.probe_executable, self._inputs.docker_executable):
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode) or not os.access(path, os.X_OK):
                raise StagingPhaseCompositionUnavailable
        working = self._inputs.working_directory.stat()
        if (
            not self._inputs.working_directory.is_dir()
            or working.st_uid != os.geteuid() or stat.S_IMODE(working.st_mode) & 0o077
            or any(self._inputs.working_directory.iterdir())
        ):
            raise StagingPhaseCompositionUnavailable
        for path in (self._inputs.compose_file,):
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
                raise StagingPhaseCompositionUnavailable
        for path in (
            self._inputs.authorization_file, self._inputs.runtime_environment_file,
            self._inputs.image_environment_file,
        ):
            metadata = path.stat()
            if (
                not stat.S_ISREG(metadata.st_mode) or path.is_symlink()
                or metadata.st_uid != os.geteuid() or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
            ):
                raise StagingPhaseCompositionUnavailable


class PrivateStagingEvidenceObjectSink:
    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path) or not root.is_absolute():
            raise ValueError("staging evidence root must be absolute")
        self._root = root
        self._validate_root()

    def __repr__(self) -> str:
        return "PrivateStagingEvidenceObjectSink()"

    def store(self, reduced: ReducedPhaseOutput) -> StagingPhaseEvidence:
        temporary = None
        try:
            if type(reduced) is not ReducedPhaseOutput or reduced.phase not in PHASES:
                raise StagingPhaseCompositionUnavailable
            self._validate_root()
            digest = hashlib.sha256(reduced.content).hexdigest()
            temporary = self._root / f".{uuid.uuid4().hex}.tmp"
            final = self._root / f"{reduced.phase}-{digest}.json"
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            try:
                remaining = memoryview(reduced.content)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written < 1:
                        raise StagingPhaseCompositionUnavailable
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.link(temporary, final)
            directory = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            if hashlib.sha256(final.read_bytes()).hexdigest() != digest:
                raise StagingPhaseCompositionUnavailable
            return StagingPhaseEvidence(
                reduced.status, f"evidence:{digest}", digest,
            )
        except StagingPhaseCompositionUnavailable:
            raise
        except Exception:
            raise StagingPhaseCompositionUnavailable from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _validate_root(self) -> None:
        try:
            metadata = self._root.stat()
            if (
                not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077 or self._root.is_symlink()
            ):
                raise StagingPhaseCompositionUnavailable
        except StagingPhaseCompositionUnavailable:
            raise
        except Exception:
            raise StagingPhaseCompositionUnavailable from None


class ComposedStagingPhaseRunner:
    __slots__ = ("_commands", "_processes", "_sink")

    def __init__(self, commands: FixedStagingPhaseCommands,
                 processes: BoundedProcessRunner,
                 sink: PrivateStagingEvidenceObjectSink) -> None:
        self._commands, self._processes, self._sink = commands, processes, sink

    def __repr__(self) -> str:
        return "ComposedStagingPhaseRunner()"

    def run(self, phase: str, authorization: StagingRunAuthorization) -> StagingPhaseEvidence:
        try:
            request = self._commands.request(phase, authorization)
            observation = self._processes.run(
                request.argv, cwd=request.cwd, environment=request.environment,
                timeout_seconds=request.timeout_seconds,
                maximum_output_bytes=request.maximum_output_bytes,
                terminate_grace_seconds=request.terminate_grace_seconds,
            )
            return self._sink.store(reduce_phase_output(phase, observation))
        except Exception:
            raise StagingPhaseCompositionUnavailable from None


def compose_staging_phase_runner(
    inputs: StagingProcessInputs, evidence_root: Path,
    *, processes: BoundedProcessRunner | None = None,
) -> ComposedStagingPhaseRunner:
    return ComposedStagingPhaseRunner(
        FixedStagingPhaseCommands(inputs),
        processes or LocalBoundedProcessRunner(),
        PrivateStagingEvidenceObjectSink(evidence_root),
    )
