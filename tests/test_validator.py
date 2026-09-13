"""
Unit Tests for IndustrialDataValidator and Atomic/Time-Series Validation Rules.
"""
import pytest
from datetime import datetime, timezone, timedelta

from src.models.data_point import PIDataPoint
from src.models.validation_result import AnomalyType, ValidationSeverity
from src.validation.rules import (
    MissingDataRule,
    DigitalStateRule,
    DataTypeRule,
    OperationalLimitsRule,
    TimeSeriesValidationRules
)


def test_valid_point_passes(validator, sample_tag_temp):
    point = PIDataPoint(
        timestamp=datetime.now(timezone.utc),
        value=65.0,
        UnitsAbbreviation="degC",
        Good=True
    )
    result = validator.validate_point(point, sample_tag_temp)
    assert result.is_valid is True
    assert len(result.anomalies) == 0


def test_missing_value_detection(sample_tag_temp):
    rule = MissingDataRule()
    point = PIDataPoint(timestamp=datetime.now(timezone.utc), value=None, Good=False)
    anomalies = rule.evaluate(point, sample_tag_temp)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.MISSING_VALUE
    assert anomalies[0].severity == ValidationSeverity.ERROR


def test_bad_digital_state_detection(sample_tag_temp):
    rule = DigitalStateRule()
    # 1. Digital State dict
    point1 = PIDataPoint(
        timestamp=datetime.now(timezone.utc),
        value={"Name": "Bad Input", "Value": 255},
        Good=False
    )
    anoms1 = rule.evaluate(point1, sample_tag_temp)
    assert len(anoms1) == 1
    assert anoms1[0].anomaly_type == AnomalyType.BAD_DIGITAL_STATE

    # 2. String error state
    point2 = PIDataPoint(
        timestamp=datetime.now(timezone.utc),
        value="Shutdown",
        Good=False
    )
    anoms2 = rule.evaluate(point2, sample_tag_temp)
    assert len(anoms2) == 1
    assert anoms2[0].anomaly_type == AnomalyType.BAD_DIGITAL_STATE


def test_non_numeric_type_detection(sample_tag_temp):
    rule = DataTypeRule()
    point = PIDataPoint(
        timestamp=datetime.now(timezone.utc),
        value="corrupted_text_payload",
        Good=True
    )
    anomalies = rule.evaluate(point, sample_tag_temp)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.NON_NUMERIC_TYPE


def test_operational_limits_detection(sample_tag_temp):
    rule = OperationalLimitsRule()
    now = datetime.now(timezone.utc)

    # HiHi Breach (Target=65, Hi=85, HiHi=95)
    p_hihi = PIDataPoint(timestamp=now, value=96.5, Good=True)
    anom_hihi = rule.evaluate(p_hihi, sample_tag_temp)
    assert len(anom_hihi) == 1
    assert anom_hihi[0].anomaly_type == AnomalyType.OUT_OF_LIMITS_HIHI
    assert anom_hihi[0].severity == ValidationSeverity.CRITICAL

    # Hi Warning Breach (value=88.0)
    p_hi = PIDataPoint(timestamp=now, value=88.0, Good=True)
    anom_hi = rule.evaluate(p_hi, sample_tag_temp)
    assert len(anom_hi) == 1
    assert anom_hi[0].anomaly_type == AnomalyType.OUT_OF_LIMITS_HI
    assert anom_hi[0].severity == ValidationSeverity.WARNING

    # LoLo Breach (LoLo=10, value=8.5)
    p_lolo = PIDataPoint(timestamp=now, value=8.5, Good=True)
    anom_lolo = rule.evaluate(p_lolo, sample_tag_temp)
    assert len(anom_lolo) == 1
    assert anom_lolo[0].anomaly_type == AnomalyType.OUT_OF_LIMITS_LOLO

    # Lo Warning Breach (Lo=20, value=15.0)
    p_lo = PIDataPoint(timestamp=now, value=15.0, Good=True)
    anom_lo = rule.evaluate(p_lo, sample_tag_temp)
    assert len(anom_lo) == 1
    assert anom_lo[0].anomaly_type == AnomalyType.OUT_OF_LIMITS_LO


def test_duplicate_timestamps_detection(sample_tag_temp):
    now = datetime.now(timezone.utc)
    points = [
        PIDataPoint(timestamp=now, value=65.0, Good=True),
        PIDataPoint(timestamp=now, value=65.1, Good=True),  # Duplicate timestamp
        PIDataPoint(timestamp=now + timedelta(seconds=10), value=65.2, Good=True),
    ]
    anomalies = TimeSeriesValidationRules.detect_duplicates(points, sample_tag_temp.tag_name)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.DUPLICATE_TIMESTAMP


def test_rate_of_change_spike_detection(sample_tag_temp):
    # Max rate is 5.0 degC / min
    now = datetime.now(timezone.utc)
    points = [
        PIDataPoint(timestamp=now, value=60.0, Good=True),
        PIDataPoint(timestamp=now + timedelta(seconds=60), value=85.0, Good=True),  # Jump of 25.0 in 1 min
    ]
    anomalies = TimeSeriesValidationRules.detect_rate_of_change_spikes(points, sample_tag_temp)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.RATE_OF_CHANGE_SPIKE


def test_flatline_sensor_freeze_detection(sample_tag_temp):
    # Max flatline points = 4
    now = datetime.now(timezone.utc)
    points = [
        PIDataPoint(timestamp=now + timedelta(seconds=i * 10), value=62.0, Good=True)
        for i in range(5)
    ]
    anomalies = TimeSeriesValidationRules.detect_flatline(points, sample_tag_temp)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.SIGNAL_FLATLINE


def test_full_time_series_validation_report(validator, sample_tag_temp):
    now = datetime.now(timezone.utc)
    points = [
        PIDataPoint(timestamp=now, value=65.0, Good=True),
        PIDataPoint(timestamp=now + timedelta(seconds=10), value=98.0, Good=True), # Out of limits HiHi
        PIDataPoint(timestamp=now + timedelta(seconds=20), value=None, Good=False), # Missing
    ]
    report = validator.validate_time_series(points, sample_tag_temp)
    assert report.total_points_evaluated == 3
    assert report.valid_points_count == 1
    assert report.data_quality_score == 33.33
    assert report.status_summary == "CRITICAL"
