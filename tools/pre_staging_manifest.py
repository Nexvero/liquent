#!/usr/bin/env python3
"""Compatibility CLI alias for the installable pre-staging capability."""

import sys

from liquent_platform.capabilities import pre_staging_manifest as _implementation


if __name__ == "__main__":
    raise SystemExit(_implementation.main())

sys.modules[__name__] = _implementation
