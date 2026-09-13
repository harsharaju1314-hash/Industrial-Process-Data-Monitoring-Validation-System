"""
AVEVA OSIsoft PI Web API Client.
Implements standard REST endpoints for PI Point discovery, snapshot values, and historical streams.
Includes built-in simulated plant provider for local offline testing when live PI server is unreachable.
"""
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from config.settings import settings
from src.client.auth import PIAuthHandler
from src.client.exceptions import (
    PIException,
    PIConnectionError,
    PIAuthenticationError,
    PINotFoundError,
    PIResponseError,
    PITimeoutError
)
from src.models.data_point import PIDataPoint, StreamResponse

logger = logging.getLogger(__name__)


class PIWebApiClient:
    """
    REST Client for AVEVA OSIsoft PI Web API.
    
    Standard PI Web API Endpoints implemented:
      - GET /points?path=\\SERVER\\TAG_NAME
      - GET /streams/{webId}/value (Snapshot current reading)
      - GET /streams/{webId}/recorded (Historical recorded readings)
      - GET /streams/{webId}/interpolated (Evenly-spaced historical readings)
      - GET /dataservers?name=SERVER_NAME
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_handler: Optional[PIAuthHandler] = None,
        verify_ssl: Optional[bool] = None,
        timeout: Optional[int] = None,
        force_mock: bool = False
    ):
        self.base_url = (base_url or settings.PI_WEB_API_URL).rstrip("/")
        self.auth_handler = auth_handler or PIAuthHandler()
        self.verify_ssl = settings.PI_VERIFY_SSL if verify_ssl is None else verify_ssl
        self.timeout = timeout or settings.PI_TIMEOUT_SECONDS
        self.session = requests.Session()
        self.session.headers.update(self.auth_handler.get_headers())
        auth = self.auth_handler.get_requests_auth()
        if auth:
            self.session.auth = auth

        self.is_mock = force_mock or settings.is_mock_mode()
        if self.is_mock:
            logger.info("PIWebApiClient initialized in SIMULATED/MOCK mode.")
        else:
            logger.info(f"PIWebApiClient initialized targeting Live PI Web API at {self.base_url}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Validates HTTP status code and parses JSON payload from PI Web API."""
        if response.status_code in (200, 201):
            try:
                return response.json()
            except ValueError as e:
                raise PIResponseError(f"Failed to parse JSON response from PI Web API: {str(e)}", response.status_code)

        if response.status_code in (401, 403):
            raise PIAuthenticationError(
                f"PI Web API Authentication Failed: HTTP {response.status_code}. Verify credentials/permissions.",
                response.status_code
            )
        elif response.status_code == 404:
            raise PINotFoundError(
                f"Requested PI resource not found: HTTP 404. Check Tag Name or WebID. Response: {response.text}",
                response.status_code
            )
        elif response.status_code >= 500:
            raise PIResponseError(
                f"PI Web API Internal Server Error: HTTP {response.status_code}. Details: {response.text}",
                response.status_code
            )
        else:
            raise PIException(
                f"Unexpected PI Web API response: HTTP {response.status_code}. Content: {response.text}",
                response.status_code
            )

    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity to the PI Web API service and verifies Data Server availability."""
        if self.is_mock:
            return {
                "status": "CONNECTED_SIMULATED",
                "message": "Connected to High-Fidelity Industrial Process Simulator",
                "server_version": "PI Web API 2023 R2 (Simulation Mode)",
                "data_server": settings.PI_DATA_SERVER_NAME,
                "is_mock": True
            }

        url = f"{self.base_url}/dataservers"
        try:
            response = self.session.get(
                url,
                params={"name": settings.PI_DATA_SERVER_NAME},
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            data = self._handle_response(response)
            return {
                "status": "CONNECTED_LIVE",
                "message": "Successfully connected to Live PI Web API Server",
                "server_details": data,
                "is_mock": False
            }
        except Timeout:
            raise PITimeoutError(f"Connection to PI Web API timed out after {self.timeout}s.")
        except ConnectionError as e:
            raise PIConnectionError(f"Could not reach PI Web API server at {self.base_url}. Network error: {str(e)}")
        except RequestException as e:
            raise PIConnectionError(f"HTTP request error during connection test: {str(e)}")

    def get_point_by_path(self, tag_path: str) -> Dict[str, Any]:
        """
        Retrieves PI Point metadata and WebID using standard PI Point Path.
        Endpoint: GET /points?path=\\SERVER\\TAG_NAME
        """
        if self.is_mock:
            tag_name = tag_path.replace("/", "\\").split("\\")[-1]
            return {
                "WebId": f"F1DP_MOCK_{tag_name}",
                "Name": tag_name,
                "Path": tag_path,
                "PointType": "Float32",
                "EngineeringUnits": "degC" if "TEMP" in tag_name else "bar"
            }

        url = f"{self.base_url}/points"
        try:
            response = self.session.get(
                url,
                params={"path": tag_path},
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Timeout:
            raise PITimeoutError(f"Request for point path '{tag_path}' timed out.")
        except ConnectionError as e:
            raise PIConnectionError(f"Connection failed while retrieving point '{tag_path}': {str(e)}")

    def get_stream_value(self, web_id: str, tag_name: Optional[str] = None) -> PIDataPoint:
        """
        Retrieves the snapshot (latest recorded) value for a specific PI Point WebID.
        Endpoint: GET /streams/{webId}/value
        """
        if self.is_mock:
            return self._generate_simulated_snapshot(tag_name or "REACTOR_01_TEMP", web_id)

        url = f"{self.base_url}/streams/{web_id}/value"
        try:
            response = self.session.get(
                url,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            data = self._handle_response(response)
            point = PIDataPoint(
                timestamp=data.get("Timestamp"),
                value=data.get("Value"),
                UnitsAbbreviation=data.get("UnitsAbbreviation", ""),
                Good=data.get("Good", True),
                Questionable=data.get("Questionable", False),
                Substituted=data.get("Substituted", False),
                Annotated=data.get("Annotated", False),
                tag_name=tag_name
            )
            return point
        except Timeout:
            raise PITimeoutError(f"Snapshot retrieval timed out for WebId: {web_id}")
        except ConnectionError as e:
            raise PIConnectionError(f"Connection failed during snapshot query: {str(e)}")

    def get_stream_recorded(
        self,
        web_id: str,
        start_time: str = "*-2h",
        end_time: str = "*",
        max_count: int = 100,
        tag_name: Optional[str] = None
    ) -> StreamResponse:
        """
        Retrieves historical recorded values for a PI Point WebID over a given time range.
        Endpoint: GET /streams/{webId}/recorded?startTime=...&endTime=...
        """
        if self.is_mock:
            return self._generate_simulated_recorded(
                tag_name or "REACTOR_01_TEMP",
                web_id,
                start_time,
                end_time,
                max_count
            )

        url = f"{self.base_url}/streams/{web_id}/recorded"
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "maxCount": max_count
        }
        try:
            response = self.session.get(
                url,
                params=params,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            data = self._handle_response(response)
            items = []
            for item in data.get("Items", []):
                items.append(PIDataPoint(
                    timestamp=item.get("Timestamp"),
                    value=item.get("Value"),
                    UnitsAbbreviation=item.get("UnitsAbbreviation", ""),
                    Good=item.get("Good", True),
                    Questionable=item.get("Questionable", False),
                    Substituted=item.get("Substituted", False),
                    Annotated=item.get("Annotated", False),
                    tag_name=tag_name
                ))
            return StreamResponse(WebId=web_id, Name=tag_name, Items=items)
        except Timeout:
            raise PITimeoutError(f"Historical query timed out for WebId: {web_id}")
        except ConnectionError as e:
            raise PIConnectionError(f"Connection failed during historical recorded query: {str(e)}")

    def _generate_simulated_snapshot(self, tag_name: str, web_id: str) -> PIDataPoint:
        """Generates a realistic snapshot reading for the specified plant tag."""
        now = datetime.now(timezone.utc)
        base_targets = {
            "REACTOR_01_TEMP": 65.4,
            "REACTOR_01_PRESS": 3.48,
            "COOLING_PUMP_FLOW": 35.2,
            "COMPRESSOR_VIBRATION": 2.15,
            "STORAGE_TANK_LEVEL": 52.0
        }
        units = {
            "REACTOR_01_TEMP": "degC",
            "REACTOR_01_PRESS": "bar",
            "COOLING_PUMP_FLOW": "m3/h",
            "COMPRESSOR_VIBRATION": "mm/s",
            "STORAGE_TANK_LEVEL": "%"
        }
        target = base_targets.get(tag_name, 50.0)
        noise = random.uniform(-0.8, 0.8)
        val = round(target + noise, 2)
        
        return PIDataPoint(
            timestamp=now,
            value=val,
            UnitsAbbreviation=units.get(tag_name, ""),
            Good=True,
            Questionable=False,
            Substituted=False,
            tag_name=tag_name
        )

    def _generate_simulated_recorded(
        self,
        tag_name: str,
        web_id: str,
        start_time: str,
        end_time: str,
        count: int = 50
    ) -> StreamResponse:
        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(hours=2)
        interval_sec = (2 * 3600) / max(count, 10)

        base_params = {
            "REACTOR_01_TEMP": {"mean": 65.0, "sigma": 1.2, "unit": "degC"},
            "REACTOR_01_PRESS": {"mean": 3.5, "sigma": 0.15, "unit": "bar"},
            "COOLING_PUMP_FLOW": {"mean": 35.0, "sigma": 1.5, "unit": "m3/h"},
            "COMPRESSOR_VIBRATION": {"mean": 2.2, "sigma": 0.2, "unit": "mm/s"},
            "STORAGE_TANK_LEVEL": {"mean": 50.0, "sigma": 1.0, "unit": "%"}
        }
        params = base_params.get(tag_name, {"mean": 50.0, "sigma": 1.0, "unit": ""})
        unit = params["unit"]
        mean = params["mean"]
        sigma = params["sigma"]

        items: List[PIDataPoint] = []
        current_dt = start_dt
        current_val = mean

        for i in range(count):
            if i == 12:
                items.append(PIDataPoint(
                    timestamp=items[-1].timestamp if items else current_dt,
                    value=current_val,
                    UnitsAbbreviation=unit,
                    Good=True,
                    tag_name=tag_name
                ))
                continue

            if i == 18:
                items.append(PIDataPoint(
                    timestamp=current_dt,
                    value={"Name": "Bad Input", "Value": 255, "IsGood": False},
                    UnitsAbbreviation=unit,
                    Good=False,
                    tag_name=tag_name
                ))
                current_dt += timedelta(seconds=interval_sec)
                continue

            if i == 25:
                items.append(PIDataPoint(
                    timestamp=current_dt,
                    value=None,
                    UnitsAbbreviation=unit,
                    Good=False,
                    tag_name=tag_name
                ))
                current_dt += timedelta(seconds=interval_sec)
                continue

            if i == 32:
                alarm_val = 96.5 if "TEMP" in tag_name else (8.4 if "PRESS" in tag_name else 7.8)
                items.append(PIDataPoint(
                    timestamp=current_dt,
                    value=alarm_val,
                    UnitsAbbreviation=unit,
                    Good=True,
                    tag_name=tag_name
                ))
                current_dt += timedelta(seconds=interval_sec)
                continue

            if i == 38:
                spike_val = current_val + (25.0 if "TEMP" in tag_name else 5.0)
                items.append(PIDataPoint(
                    timestamp=current_dt,
                    value=round(spike_val, 2),
                    UnitsAbbreviation=unit,
                    Good=True,
                    tag_name=tag_name
                ))
                current_dt += timedelta(seconds=interval_sec)
                continue

            if 42 <= i <= 46:
                items.append(PIDataPoint(
                    timestamp=current_dt,
                    value=62.34 if "TEMP" in tag_name else 3.25,
                    UnitsAbbreviation=unit,
                    Good=True,
                    tag_name=tag_name
                ))
                current_dt += timedelta(seconds=interval_sec)
                continue

            step = random.gauss(0, sigma)
            current_val = round(max(0.0, current_val + step), 2)
            items.append(PIDataPoint(
                timestamp=current_dt,
                value=current_val,
                UnitsAbbreviation=unit,
                Good=True,
                tag_name=tag_name
            ))
            current_dt += timedelta(seconds=interval_sec)

        return StreamResponse(WebId=web_id, Name=tag_name, Items=items)
