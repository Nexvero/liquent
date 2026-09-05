from dataclasses import replace
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tests.test_lq1123_lq1134_engine_api_run_bound_root import run_root
from tools.engine_api_joint_staging_source_set import observe_run_bound_source_set


def _changed(value, index, replacement):
    items=list(value);items[index]=replacement;return tuple(items)


@pytest.mark.parametrize("index,replacement", ((2,stat.S_IFREG|0o700),(2,stat.S_IFDIR|0o755),(3,99999999)))
def test_source_observation_rejects_invalid_root_semantics(tmp_path,index,replacement):
    observed=observe_run_bound_source_set(run_root(tmp_path))
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(observed,root_state=_changed(observed.root_state,index,replacement))


@pytest.mark.parametrize("index,replacement", ((2,stat.S_IFDIR|0o600),(2,stat.S_IFREG|0o640),(3,99999999),(5,2),(6,0)))
def test_source_observation_rejects_invalid_child_semantics(tmp_path,index,replacement):
    observed=observe_run_bound_source_set(run_root(tmp_path));children=list(observed.child_states);children[0]=_changed(children[0],index,replacement)
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(observed,child_states=tuple(children))


def test_source_observation_rejects_child_size_above_fixed_limit(tmp_path):
    observed=observe_run_bound_source_set(run_root(tmp_path));children=list(observed.child_states);children[0]=_changed(children[0],6,1025)
    with pytest.raises(ManifestHandoffRegistryUnavailable): replace(observed,child_states=tuple(children))


def test_authentic_source_observation_satisfies_closed_invariants(tmp_path):
    observed=observe_run_bound_source_set(run_root(tmp_path));assert replace(observed)==observed
