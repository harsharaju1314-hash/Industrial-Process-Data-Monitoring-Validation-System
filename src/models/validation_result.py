"""
Validation Result, Anomaly Classification, and Summary Models.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"


class AnomalyType(str, Enum):
    MISSING_VALUE = "MISSING_VALUE"
    BAD_DIGITAL_STATE = "BAD_DIGITAL_STATE"
    NON_NUMERIC_TYPE = "NON_NUMERIC_TYPE"
    OUT_OF_LIMITS_LOLO = "OUT_OF_LIMITS_LOLO"
    OUT_OF_LIMITS_LO = "OUT_OF_LIMITS_LO"
    OUT_OF_LIMITS_HI = "OUT_OF_LIMITS_HI"
    OUT_OF_LIMITS_HIHI = "OUT_OF_LIMITS_HIHI"
    RATE_OF_CHANGE_SPIKE = "RATE_OF_CHANGE_SPIKE"
    SIGNAL_FLATLINE = "SIGNAL_FLATLINE"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    API_COMMUNICATION_ERROR = "API_COMMUNICATION_ERROR"


class ValidationAnomaly(BaseModel):
    tag_name: str
    timestamp: Optional[datetime] = None
    anomaly_type: AnomalyType
    severity: ValidationSeverity
    observed_value: Any = None
    threshold_or_rule: str
    message: str
    suggested_action: str


class DataPointValidation(BaseModel):
    tag_name: str
    timestamp: datetime
    raw_value: Any
    numeric_value: Optional[float] = None
    is_valid: bool = True
    anomalies: List[ValidationAnomaly] = Field(default_factory=list)


class TagValidationReport(BaseModel):
    tag_name: str
    description: str = ""
    engineering_units: str = ""
    total_points_evaluated: int = 0
    valid_points_count: int = 0
    missing_points_count: int = 0
    bad_state_points_count: int = 0
    out_of_limits_count: int = 0
    rate_of_change_spikes_count: int = 0
    flatline_count: int = 0
    duplicate_count: int = 0
    anomalies: List[ValidationAnomaly] = Field(default_factory=list)
    point_validations: List[DataPointValidation] = Field(default_factory=list)

    @property
    def data_quality_score(self) -> float:
        if self.total_points_evaluated == 0:
            return 0.0
        return round((self.valid_points_count / self.total_points_evaluated) * 100.0, 2)

    @property
    def status_summary(self) -> str:
        if self.total_points_evaluated == 0:
            return "NO_DATA"
        if self.data_quality_score == 100.0:
            return "HEALTHY"
        if self.data_quality_score >= 80.0:
            return "WARNING"
        return "CRITICAL"


class BatchValidationSummary(BaseModel):
    execution_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = "PI Web API"
    mode: str = "Live"
    total_tags_evaluated: int = 0
    total_data_points: int = 0
    total_valid_points: int = 0
    total_anomalies_detected: int = 0
    overall_quality_score: float = 0.0
    tag_reports: Dict[str, TagValidationReport] = Field(default_factory=dict)

    def compute_aggregates(self):
        self.total_tags_evaluated = len(self.tag_reports)
        self.total_data_points = sum(r.total_points_evaluated for r in self.tag_reports.values())
        self.total_valid_points = sum(r.valid_points_count for r in self.tag_reports.values())
        self.total_anomalies_detected = sum(len(r.anomalies) for r in self.tag_reports.values())
        if self.total_data_points > 0:
            self.overall_quality_score = round((self.total_valid_points / self.total_data_points) * 100.0, 2)
        else:
            self.overall_quality_score = 0.0
