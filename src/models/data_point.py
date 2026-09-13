"""
PI Web API Data Point and Stream Response Models.
Accurately maps to AVEVA PI Web API standard JSON schema.
"""
from datetime import datetime, timezone
from typing import Any, Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict


class DigitalState(BaseModel):
    """Represents a PI System Digital State (e.g. 'Bad Input', 'Pt Created', 'Shutdown', 'No Data')."""
    name: str = Field(..., description="State name or error label")
    code: int = Field(default=0, description="PI Digital State code index")
    set_name: str = Field(default="SYSTEM", description="PI Digital State set name")
    is_good: bool = Field(default=False, description="Whether this state indicates good data")


class PIDataPoint(BaseModel):
    """
    Standard AVEVA OSIsoft PI Web API Data Point.
    Matches the schema returned by:
      - GET /streams/{webId}/value
      - GET /streams/{webId}/recorded
      - GET /streams/{webId}/interpolated
    """
    model_config = ConfigDict(populate_by_name=True)

    timestamp: Optional[datetime] = Field(default=None, description="UTC timestamp of the reading")
    value: Optional[Union[float, int, str, bool, dict]] = Field(
        default=None, description="Sensor value or digital state object"
    )
    units_abbreviation: Optional[str] = Field(default="", alias="UnitsAbbreviation")
    good: bool = Field(default=True, alias="Good", description="PI Web API quality flag (True if good, False if bad)")
    questionable: bool = Field(default=False, alias="Questionable", description="PI Questionable flag")
    substituted: bool = Field(default=False, alias="Substituted", description="PI Substituted flag")
    annotated: bool = Field(default=False, alias="Annotated")
    tag_name: Optional[str] = Field(default=None, description="Tag name associated with this data point")

    @property
    def is_digital_state(self) -> bool:
        if isinstance(self.value, dict):
            return True
        if isinstance(self.value, str):
            known_states = {"bad input", "pt created", "shutdown", "no data", "scan off", "calc failed", "configure"}
            return self.value.strip().lower() in known_states
        return False

    @property
    def numeric_value(self) -> Optional[float]:
        if self.value is None:
            return None
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, str):
            try:
                return float(self.value)
            except ValueError:
                return None
        return None

    @property
    def state_name(self) -> Optional[str]:
        if isinstance(self.value, dict):
            return self.value.get("Name") or self.value.get("name", "Unknown State")
        if isinstance(self.value, str) and not self.numeric_value:
            return self.value
        return None


class StreamResponse(BaseModel):
    """Represents a collection of recorded/interpolated PI data points from a stream endpoint."""
    model_config = ConfigDict(populate_by_name=True)

    web_id: Optional[str] = Field(default=None, alias="WebId")
    name: Optional[str] = Field(default=None, alias="Name")
    items: List[PIDataPoint] = Field(default_factory=list, alias="Items")
