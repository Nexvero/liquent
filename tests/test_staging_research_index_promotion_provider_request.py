import pytest

from liquent_platform.adapters.staging_research_index_promotion_provider_response import (  # noqa: E501
    PendingStagingResearchIndexPromotionProviderResponse,
)
from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    RequestedStagingResearchIndexPromotionProviderTransport,
    StagingResearchIndexPromotionProviderRequestUnavailable,
    StagingResearchIndexPromotionProviderStatusRequest,
)


class Acquisition:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def acquire(self, request):
        self.calls.append(request)
        return self.response


def test_one_closed_request_is_acquired_once() -> None:
    operation_id = "promotion-2720"
    acquisition = Acquisition(
        PendingStagingResearchIndexPromotionProviderResponse(operation_id)
    )
    transport = RequestedStagingResearchIndexPromotionProviderTransport(acquisition)
    assert transport.read_operation(operation_id) == acquisition.response
    assert len(acquisition.calls) == 1
    assert acquisition.calls[0].operation_id == operation_id
    assert repr(acquisition.calls[0]) == (
        "StagingResearchIndexPromotionProviderStatusRequest()"
    )
    assert operation_id not in repr(acquisition.calls[0])


def test_neutral_absence_passes_through() -> None:
    acquisition = Acquisition(None)
    assert RequestedStagingResearchIndexPromotionProviderTransport(
        acquisition
    ).read_operation("promotion-2720") is None


@pytest.mark.parametrize("operation_id", ["", "not valid", 42, None])
def test_malformed_identity_never_reaches_acquisition(operation_id) -> None:
    acquisition = Acquisition(None)
    with pytest.raises(StagingResearchIndexPromotionProviderRequestUnavailable):
        RequestedStagingResearchIndexPromotionProviderTransport(
            acquisition
        ).read_operation(operation_id)
    assert acquisition.calls == []


def test_invalid_response_and_acquisition_failure_are_detail_free() -> None:
    with pytest.raises(StagingResearchIndexPromotionProviderRequestUnavailable):
        RequestedStagingResearchIndexPromotionProviderTransport(
            Acquisition({"status": "committed"})
        ).read_operation("promotion-2720")

    class Broken:
        def acquire(self, _request):
            raise RuntimeError("transport detail")

    with pytest.raises(StagingResearchIndexPromotionProviderRequestUnavailable) as caught:
        RequestedStagingResearchIndexPromotionProviderTransport(
            Broken()
        ).read_operation("promotion-2720")
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "transport detail" not in str(caught.value)
