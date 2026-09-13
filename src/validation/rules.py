"""
Modular Validation Rules for Industrial Process Data.
Each rule evaluates specific data quality, telemetry integrity, and operational safety criteria.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple, Any

from src.models.data_point import PIDataPoint
from src.models.tag_definition import PITag
from src.models.validation_result import ValidationAnomaly, AnomalyType, ValidationSeverity


class BaseValidationRule(ABC):
    """Abstract Base Class for all validation rules."""
    
    @abstractmethod
    def evaluate(self, point: PIDataPoint, tag_def: PITag) -> List[ValidationAnomaly]:
        """Evaluates a single point and returns a list of detected anomalies."""
        pass


class MissingDataRule(BaseValidationRule):
    """Detects missing (None / empty / null) sensor readings."""

    def evaluate(self, point: PIDataPoint, tag_def: PITag) -> List[ValidationAnomaly]:
        anomalies = []
        if point.value is None or point.timestamp is None:
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.MISSING_VALUE,
                severity=ValidationSeverity.ERROR,
                observed_value=point.value,
                threshold_or_rule="Value and Timestamp must not be null",
                message=f"Missing telemetry reading for tag '{tag_def.tag_name}'",
                suggested_action="Verify PI Interface / OPC DA/UA Connector status and network connectivity."
            ))
        return anomalies


class DigitalStateRule(BaseValidationRule):
    """
    Detects PI System Digital State errors.
    Standard PI Bad states: 'Pt Created', 'Shutdown', 'Bad Input', 'No Data', 'Scan Off', 'Calc Failed'.
    Also checks if PI Web API 'Good' quality flag is False.
    """

    def evaluate(self, point: PIDataPoint, tag_def: PITag) -> List[ValidationAnomaly]:
        anomalies = []
        if not point.good or point.is_digital_state:
            state_label = point.state_name or "System Digital State (Good=False)"
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.BAD_DIGITAL_STATE,
                severity=ValidationSeverity.CRITICAL,
                observed_value=state_label,
                threshold_or_rule="Good == True and value is valid engineering measurement",
                message=f"PI Digital State Error encountered: '{state_label}'",
                suggested_action="Inspect field transmitter wiring, calibration status, or DCS/PLC communication card."
            ))
        return anomalies


class DataTypeRule(BaseValidationRule):
    """Validates that numeric tags (Float/Int) contain valid numeric data."""

    def evaluate(self, point: PIDataPoint, tag_def: PITag) -> List[ValidationAnomaly]:
        anomalies = []
        if "Float" in tag_def.point_type or "Int" in tag_def.point_type:
            if point.value is not None and not point.is_digital_state and point.numeric_value is None:
                anomalies.append(ValidationAnomaly(
                    tag_name=tag_def.tag_name,
                    timestamp=point.timestamp,
                    anomaly_type=AnomalyType.NON_NUMERIC_TYPE,
                    severity=ValidationSeverity.ERROR,
                    observed_value=str(point.value),
                    threshold_or_rule=f"Must parse as {tag_def.point_type}",
                    message=f"Non-numeric value '{point.value}' received for numeric tag '{tag_def.tag_name}'",
                    suggested_action="Check PI Point Type configuration in PI System Management Tools (PI SMT)."
                ))
        return anomalies


class OperationalLimitsRule(BaseValidationRule):
    """
    Evaluates process readings against 4-tier industrial operational limits:
      - Low-Low (LoLo): Emergency shutdown / critical low
      - Low (Lo): Operator warning low
      - High (Hi): Operator warning high
      - High-High (HiHi): Emergency shutdown / critical high
    """

    def evaluate(self, point: PIDataPoint, tag_def: PITag) -> List[ValidationAnomaly]:
        anomalies = []
        val = point.numeric_value
        if val is None or not point.good:
            return anomalies

        limits = tag_def.limits

        # 1. Critical High-High Limit
        if limits.high_high is not None and val >= limits.high_high:
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.OUT_OF_LIMITS_HIHI,
                severity=ValidationSeverity.CRITICAL,
                observed_value=val,
                threshold_or_rule=f"HiHi Limit: {limits.high_high} {tag_def.engineering_units}",
                message=f"Critical High Limit (HiHi) Exceeded: {val} >= {limits.high_high} {tag_def.engineering_units}",
                suggested_action="Initiate emergency process cool-down/relief protocol and alert control room supervisor."
            ))
        # 2. High Warning Limit
        elif limits.high is not None and val >= limits.high:
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.OUT_OF_LIMITS_HI,
                severity=ValidationSeverity.WARNING,
                observed_value=val,
                threshold_or_rule=f"Hi Limit: {limits.high} {tag_def.engineering_units}",
                message=f"High Alarm Threshold (Hi) Reached: {val} >= {limits.high} {tag_def.engineering_units}",
                suggested_action="Adjust feed rate or cooling valve trim to restore nominal setpoint."
            ))

        # 3. Critical Low-Low Limit
        if limits.low_low is not None and val <= limits.low_low:
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.OUT_OF_LIMITS_LOLO,
                severity=ValidationSeverity.CRITICAL,
                observed_value=val,
                threshold_or_rule=f"LoLo Limit: {limits.low_low} {tag_def.engineering_units}",
                message=f"Critical Low Limit (LoLo) Breached: {val} <= {limits.low_low} {tag_def.engineering_units}",
                suggested_action="Trip booster equipment or open makeup supply to avoid starvation cavitation."
            ))
        # 4. Low Warning Limit
        elif limits.low is not None and val <= limits.low:
            anomalies.append(ValidationAnomaly(
                tag_name=tag_def.tag_name,
                timestamp=point.timestamp,
                anomaly_type=AnomalyType.OUT_OF_LIMITS_LO,
                severity=ValidationSeverity.WARNING,
                observed_value=val,
                threshold_or_rule=f"Lo Limit: {limits.low} {tag_def.engineering_units}",
                message=f"Low Alarm Threshold (Lo) Reached: {val} <= {limits.low} {tag_def.engineering_units}",
                suggested_action="Verify inlet valve position and suction pressure."
            ))

        return anomalies


class TimeSeriesValidationRules:
    """Multi-point time-series validation rules (Duplicates, Rate of Change, Flatline)."""

    @staticmethod
    def detect_duplicates(points: List[PIDataPoint], tag_name: str) -> List[ValidationAnomaly]:
        """Identifies duplicate timestamps within a time-series dataset."""
        anomalies = []
        seen_timestamps = set()

        for p in points:
            if p.timestamp is None:
                continue
            ts_str = p.timestamp.isoformat()
            if ts_str in seen_timestamps:
                anomalies.append(ValidationAnomaly(
                    tag_name=tag_name,
                    timestamp=p.timestamp,
                    anomaly_type=AnomalyType.DUPLICATE_TIMESTAMP,
                    severity=ValidationSeverity.WARNING,
                    observed_value=p.value,
                    threshold_or_rule="Timestamps in time-series must be strictly monotonic",
                    message=f"Duplicate timestamp event detected at {ts_str}",
                    suggested_action="Check PI Buffer Subsystem or historian compression/exception settings."
                ))
            else:
                seen_timestamps.add(ts_str)
        return anomalies

    @staticmethod
    def detect_rate_of_change_spikes(
        points: List[PIDataPoint],
        tag_def: PITag
    ) -> List[ValidationAnomaly]:
        """Detects sudden, physically impossible jumps between consecutive readings."""
        anomalies = []
        max_rate = tag_def.limits.max_rate_of_change_per_minute
        if max_rate is None or len(points) < 2:
            return anomalies

        sorted_pts = sorted(
            [p for p in points if p.timestamp and p.numeric_value is not None and p.good],
            key=lambda x: x.timestamp
        )

        for i in range(1, len(sorted_pts)):
            prev_p = sorted_pts[i - 1]
            curr_p = sorted_pts[i]

            time_diff_sec = (curr_p.timestamp - prev_p.timestamp).total_seconds()
            if time_diff_sec <= 0:
                continue

            time_diff_min = time_diff_sec / 60.0
            val_change = abs(curr_p.numeric_value - prev_p.numeric_value)
            rate_per_min = val_change / time_diff_min

            if rate_per_min > max_rate:
                anomalies.append(ValidationAnomaly(
                    tag_name=tag_def.tag_name,
                    timestamp=curr_p.timestamp,
                    anomaly_type=AnomalyType.RATE_OF_CHANGE_SPIKE,
                    severity=ValidationSeverity.WARNING,
                    observed_value=f"{round(rate_per_min, 2)} {tag_def.engineering_units}/min",
                    threshold_or_rule=f"Max Allowed Rate: {max_rate} {tag_def.engineering_units}/min",
                    message=f"Sudden rate of change spike detected ({round(rate_per_min, 2)}/min) from {prev_p.numeric_value} to {curr_p.numeric_value}",
                    suggested_action="Inspect transmitter for electrical noise or ground loop interference."
                ))

        return anomalies

    @staticmethod
    def detect_flatline(
        points: List[PIDataPoint],
        tag_def: PITag
    ) -> List[ValidationAnomaly]:
        """Detects sensor freezing / flatline conditions where value does not fluctuate."""
        anomalies = []
        max_flat = tag_def.limits.max_flatline_points
        tol = tag_def.limits.flatline_tolerance
        if len(points) < max_flat:
            return anomalies

        sorted_pts = [p for p in points if p.timestamp and p.numeric_value is not None and p.good]
        if len(sorted_pts) < max_flat:
            return anomalies

        consecutive_count = 1
        for i in range(1, len(sorted_pts)):
            prev_val = sorted_pts[i - 1].numeric_value
            curr_val = sorted_pts[i].numeric_value

            if abs(curr_val - prev_val) <= tol:
                consecutive_count += 1
                if consecutive_count == max_flat:
                    anomalies.append(ValidationAnomaly(
                        tag_name=tag_def.tag_name,
                        timestamp=sorted_pts[i].timestamp,
                        anomaly_type=AnomalyType.SIGNAL_FLATLINE,
                        severity=ValidationSeverity.WARNING,
                        observed_value=curr_val,
                        threshold_or_rule=f">= {max_flat} consecutive points within +- {tol} {tag_def.engineering_units}",
                        message=f"Sensor signal flatline detected at value {curr_val} across {max_flat} consecutive readings",
                        suggested_action="Check if field sensor is stuck, frozen, or transmitter sensing line is clogged."
                    ))
            else:
                consecutive_count = 1

        return anomalies
