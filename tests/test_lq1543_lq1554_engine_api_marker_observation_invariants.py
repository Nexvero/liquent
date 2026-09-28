from dataclasses import replace
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import encode_staging_run_acceptance, observe_staging_run_acceptance
from tests.test_lq1123_lq1134_engine_api_run_bound_root import RUN
from tests.test_lq1135_lq1146_engine_api_run_acceptance import roots
from tests.test_lq1159_lq1170_engine_api_acceptance_audit import accept


def _changed(value,index,replacement):
    items=list(value);items[index]=replacement;return tuple(items)


@pytest.mark.parametrize("index,replacement", ((2,stat.S_IFDIR|0o600),(2,stat.S_IFREG|0o640),(3,99999999),(5,2),(6,0),(6,1025)))
def test_marker_observation_rejects_invalid_file_semantics(tmp_path,index,replacement):
    source,registry=roots(tmp_path);accept(source,registry);observed=observe_staging_run_acceptance(registry,RUN)
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(observed,marker_state=_changed(observed.marker_state,index,replacement))


def test_marker_observation_requires_exact_canonical_size(tmp_path):
    source,registry=roots(tmp_path);accept(source,registry);observed=observe_staging_run_acceptance(registry,RUN);expected=len(encode_staging_run_acceptance(observed.acceptance))
    assert observed.marker_state[6]==expected
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(observed,marker_state=_changed(observed.marker_state,6,expected+1))


def test_authentic_marker_observation_satisfies_closed_invariants(tmp_path):
    source,registry=roots(tmp_path);accept(source,registry);observed=observe_staging_run_acceptance(registry,RUN);assert replace(observed)==observed
