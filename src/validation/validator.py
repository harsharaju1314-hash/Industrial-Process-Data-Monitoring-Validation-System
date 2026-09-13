"""
Industrial Data Validation Engine.
Applies all atomic and multi-point rules to evaluate data quality and operational safety.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.models.tag_definition import PITag
from src.models.data_point import PIDataPoint
from src.models.validation_result import (
    DataPointValidation,
    TagValidationReport,
    BatchValidationSummary,
    ValidationAnomaly,
    AnomalyType
)
from src.validation.rules import (
    MissingDataRule,
    DigitalStateRule,
    DataTypeRule,
    OperationalLimitsRule,
    TimeSeriesValidationRules
)

logger = logging.getLogger(__name__)


class IndustrialDataValidator:
    """Core Validation Engine for AVEVA OSIsoft PI telemetry."""

    def __init__(self):
        self.point_rules = [
            MissingDataRule(),
            DigitalStateRule(),
            DataTypeRule(),
            OperationalLimitsRule()
        ]

    def validate_point(self, point: PIDataPoint, tag_def: PITag) -> DataPointValidation:
        """Evaluates a single PI data point against all atomic point rules."""
        anomalies: List[ValidationAnomaly] = []

        for rule in self.point_rules:
            anomalies.extend(rule.evaluate(point, tag_def))

        is_valid = len(anomalies) == 0
        return DataPointValidation(
            tag_name=tag_def.tag_name,
            timestamp=point.timestamp or datetime.utcnow(),
            raw_value=point.value,
            numeric_value=point.numeric_value,
            is_valid=is_valid,
            anomalies=anomalies
        )

    def validate_time_series(
        self,
        points: List[PIDataPoint],
        tag_def: PITag
    ) -> TagValidationReport:
        """
        Validates a full time-series dataset for a specific tag.
        Combines point-level evaluations and multi-point time-series algorithms.
        """
        report = TagValidationReport(
            tag_name=tag_def.tag_name,
            description=tag_def.description,
            engineering_units=tag_def.engineering_units,
            total_points_evaluated=len(points)
        )

        all_anomalies: List[ValidationAnomaly] = []
        point_validations: List[DataPointValidation] = []

        valid_count = 0
        for pt in points:
            pt_val = self.validate_point(pt, tag_def)
            point_validations.append(pt_val)
            if pt_val.is_valid:
                valid_count += 1
            else:
                all_anomalies.extend(pt_val.anomalies)
                for anom in pt_val.anomalies:
                    if anom.anomaly_type == AnomalyType.MISSING_VALUE:
                        report.missing_points_count += 1
                    elif anom.anomaly_type == AnomalyType.BAD_DIGITAL_STATE:
                        report.bad_state_points_count += 1
                    elif "OUT_OF_LIMITS" in anom.anomaly_type.value:
                        report.out_of_limits_count += 1

        report.valid_points_count = valid_count
        report.point_validations = point_validations

        duplicates = TimeSeriesValidationRules.detect_duplicates(points, tag_def.tag_name)
        if duplicates:
            report.duplicate_count = len(duplicates)
            all_anomalies.extend(duplicates)

        roc_spikes = TimeSeriesValidationRules.detect_rate_of_change_spikes(points, tag_def)
        if roc_spikes:
            report.rate_of_change_spikes_count = len(roc_spikes)
            all_anomalies.extend(roc_spikes)

        flatlines = TimeSeriesValidationRules.detect_flatline(points, tag_def)
        if flatlines:
            report.flatline_count = len(flatlines)
            all_anomalies.extend(flatlines)

        report.anomalies = all_anomalies
        return report

    def validate_batch(
        self,
        telemetry_map: Dict[str, List[PIDataPoint]],
        tag_definitions: Dict[str, PITag],
        is_mock_mode: bool = False
    ) -> BatchValidationSummary:
        """Validates telemetry across multiple tags and generates a batch quality report."""
        summary = BatchValidationSummary(
            mode="Simulated" if is_mock_mode else "Live"
        )

        for tag_name, points in telemetry_map.items():
            tag_def = tag_definitions.get(tag_name)
            if not tag_def:
                tag_def = PITag(tag_name=tag_name)
            report = self.validate_time_series(points, tag_def)
            summary.tag_reports[tag_name] = report

        summary.compute_aggregates()
        return summary
