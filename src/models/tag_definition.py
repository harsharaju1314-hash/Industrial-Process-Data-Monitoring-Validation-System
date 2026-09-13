"""
Tag Definition and Engineering Limits Data Models.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TagLimitConfig(BaseModel):
    """Operational limits and anomaly detection thresholds for a PI tag."""
    low_low: Optional[float] = Field(default=None, description="Critical low alarm limit (LoLo)")
    low: Optional[float] = Field(default=None, description="Warning low alarm limit (Lo)")
    target: Optional[float] = Field(default=None, description="Nominal operational setpoint")
    high: Optional[float] = Field(default=None, description="Warning high alarm limit (Hi)")
    high_high: Optional[float] = Field(default=None, description="Critical high alarm limit (HiHi)")
    max_rate_of_change_per_minute: Optional[float] = Field(
        default=None, description="Maximum physically plausible change per minute"
    )
    flatline_tolerance: float = Field(
        default=0.001, description="Absolute variance threshold below which signal is considered frozen"
    )
    max_flatline_points: int = Field(
        default=5, description="Number of consecutive identical readings before raising flatline anomaly"
    )


class PITag(BaseModel):
    """PI Point / Tag metadata definition."""
    tag_name: str = Field(..., description="PI Tag name (e.g. REACTOR_01_TEMP)")
    point_type: str = Field(default="Float32", description="Data type (Float32, Float64, Int32, Digital, String)")
    engineering_units: str = Field(default="", description="Units of measure (e.g. degC, bar, %)")
    description: str = Field(default="", description="Human readable description of tag")
    web_id: Optional[str] = Field(default=None, description="AVEVA PI Web API 128-bit base64 WebID")
    limits: TagLimitConfig = Field(default_factory=TagLimitConfig)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
