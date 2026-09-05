#!/usr/bin/env python3
"""Compatibility CLI alias for the installable reconciliation capability."""

import sys

from liquent_platform.capabilities import (
    private_manifest_handoff_reconcile as _implementation,
)


if __name__ == "__main__":
    raise SystemExit(_implementation.main())

sys.modules[__name__] = _implementation
