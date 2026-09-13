"""
Pytest Fixtures and Test Harness for PI Web API & Validation System.
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from src.models.tag_definition import PITag, TagLimitConfig
from src.models.data_point import PIDataPoint, StreamResponse
from src.client.pi_client import PIWebApiClient
from src.retrieval.data_service import PIDataService
from src.validation.validator import IndustrialDataValidator


@pytest.fixture
def sample_tag_temp() -> PITag:
    """Fixture for a standard temperature PI Tag with full 4-tier alarm limits."""
    return PITag(
        tag_name="REACTOR_01_TEMP",
        point_type="Float32",
        engineering_units="degC",
        description="Reactor Core Temperature",
        web_id="F1DP_TEST_TEMP",
        limits=TagLimitConfig(
            low_low=10.0,
            low=20.0,
            target=65.0,
            high=85.0,
            high_high=95.0,
            max_rate_of_change_per_minute=5.0,
            flatline_tolerance=0.01,
            max_flatline_points=4
        )
    )


@pytest.fixture
def sample_tag_press() -> PITag:
    """Fixture for a pressure PI Tag."""
    return PITag(
        tag_name="REACTOR_01_PRESS",
        point_type="Float32",
        engineering_units="bar",
        description="Reactor Internal Pressure",
        web_id="F1DP_TEST_PRESS",
        limits=TagLimitConfig(
            low_low=0.5,
            low=1.0,
            target=3.5,
            high=6.0,
            high_high=8.0,
            max_rate_of_change_per_minute=1.5,
            flatline_tolerance=0.005,
            max_flatline_points=4
        )
    )


@pytest.fixture
def mock_pi_client() -> PIWebApiClient:
    """Fixture for PI Web API Client forced in simulation/mock mode."""
    return PIWebApiClient(force_mock=True)


@pytest.fixture
def data_service(mock_pi_client) -> PIDataService:
    """Fixture for Data Service wired with mock client."""
    return PIDataService(client=mock_pi_client)


@pytest.fixture
def validator() -> IndustrialDataValidator:
    """Fixture for Industrial Data Validator engine."""
    return IndustrialDataValidator()
