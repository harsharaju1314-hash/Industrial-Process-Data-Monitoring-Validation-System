"""
Unit Tests for PIDataService layer.
"""
import pytest
from src.retrieval.data_service import PIDataService
from src.client.exceptions import PINotFoundError


def test_list_and_get_configured_tags(data_service):
    tags = data_service.list_tags()
    assert len(tags) >= 5
    temp_tag = data_service.get_tag_definition("REACTOR_01_TEMP")
    assert temp_tag is not None
    assert temp_tag.engineering_units == "degC"


def test_get_snapshot(data_service):
    point = data_service.get_snapshot("REACTOR_01_TEMP")
    assert point.tag_name == "REACTOR_01_TEMP"
    assert point.numeric_value is not None
    assert point.good is True


def test_get_all_snapshots(data_service):
    snapshots = data_service.get_all_snapshots()
    assert "REACTOR_01_TEMP" in snapshots
    assert "REACTOR_01_PRESS" in snapshots
    assert len(snapshots) >= 5


def test_get_historical_data_valid(data_service):
    points = data_service.get_historical_data("REACTOR_01_TEMP", start_time="*-2h", end_time="*", max_count=20)
    assert len(points) == 20
    assert all(p.tag_name == "REACTOR_01_TEMP" for p in points)


def test_get_historical_data_unknown_tag(data_service):
    with pytest.raises(PINotFoundError):
        data_service.get_historical_data("UNKNOWN_NONEXISTENT_TAG")
