"""Explicitly owned SIGTERM/SIGINT stop source for the Engine API proxy."""

from __future__ import annotations

import signal
import threading

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class OwnedManifestHandoffSupervisorEngineApiSignalStopSource:
    """Install minimal stop handlers and restore every prior handler explicitly."""

    __slots__ = ("_active", "_installed", "_originals", "_requested")

    def __init__(self) -> None:
        self._active = False
        self._requested = False
        self._originals = {}
        self._installed = []

    def __repr__(self) -> str:
        return "OwnedManifestHandoffSupervisorEngineApiSignalStopSource()"

    def install(self) -> None:
        if (
            self._active
            or threading.current_thread() is not threading.main_thread()
        ):
            raise ManifestHandoffRegistryUnavailable
        signals = (signal.SIGTERM, signal.SIGINT)
        try:
            originals = {number: signal.getsignal(number) for number in signals}
            self._requested = False
            self._originals = originals
            self._installed = []
            for number in signals:
                signal.signal(number, self._handle)
                self._installed.append(number)
            self._active = True
        except Exception:
            for number in reversed(self._installed):
                try:
                    signal.signal(number, self._originals[number])
                except Exception:
                    pass
            self._originals = {}
            self._installed = []
            self._active = False
            raise ManifestHandoffRegistryUnavailable from None

    def requested(self) -> bool:
        return self._requested

    def restore(self) -> None:
        if not self._active:
            raise ManifestHandoffRegistryUnavailable
        failed = False
        for number in reversed(self._installed):
            try:
                signal.signal(number, self._originals[number])
            except Exception:
                failed = True
        self._originals = {}
        self._installed = []
        self._active = False
        if failed:
            raise ManifestHandoffRegistryUnavailable

    def _handle(self, number, frame) -> None:
        if self._active and number in (signal.SIGTERM, signal.SIGINT):
            self._requested = True
