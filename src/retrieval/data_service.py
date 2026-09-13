"""
Industrial Data Retrieval Service.
Orchestrates tag resolution, snapshot querying, and historical time-range telemetry ingestion.
"""
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from config.settings import settings
from src.client.pi_client import PIWebApiClient
from src.client.exceptions import PIException, PINotFoundError
from src.models.tag_definition import PITag
from src.models.data_point import PIDataPoint, StreamResponse

logger = logging.getLogger(__name__)


class PIDataService:
    """Service layer for fetching industrial process data from PI Web API."""

    def __init__(
        self,
        client: Optional[PIWebApiClient] = None,
        tags_config_path: Optional[Path] = None
    ):
        self.client = client or PIWebApiClient()
        self.tags_config_path = tags_config_path or settings.TAGS_CONFIG_PATH
        self.configured_tags: Dict[str, PITag] = self._load_tag_definitions()

    def _load_tag_definitions(self) -> Dict[str, PITag]:
        """Loads configured tags and their operational limits from JSON config."""
        tags_map = {}
        if not self.tags_config_path.exists():
            logger.warning(f"Tags config file not found at {self.tags_config_path}. Using empty registry.")
            return tags_map

        try:
            with open(self.tags_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for tag_dict in data.get("tags", []):
                    tag = PITag(**tag_dict)
                    tags_map[tag.tag_name] = tag
            logger.info(f"Loaded {len(tags_map)} tag definitions from {self.tags_config_path.name}")
        except Exception as e:
            logger.error(f"Failed to load tag definitions from {self.tags_config_path}: {str(e)}")
        return tags_map

    def get_tag_definition(self, tag_name: str) -> Optional[PITag]:
        """Returns PITag metadata model for a given tag name."""
        return self.configured_tags.get(tag_name)

    def list_tags(self) -> List[PITag]:
        """Returns list of all configured tags."""
        return list(self.configured_tags.values())

    def get_snapshot(self, tag_name: str) -> PIDataPoint:
        """
        Retrieves the current real-time snapshot value for a single tag.
        Handles WebID resolution automatically.
        """
        tag = self.get_tag_definition(tag_name)
        web_id = tag.web_id if tag and tag.web_id else f"MOCK_{tag_name}"
        
        try:
            point = self.client.get_stream_value(web_id=web_id, tag_name=tag_name)
            if tag and not point.units_abbreviation:
                point.units_abbreviation = tag.engineering_units
            return point
        except PIException as e:
            logger.error(f"Snapshot retrieval failed for tag '{tag_name}': {str(e)}")
            raise

    def get_all_snapshots(self) -> Dict[str, PIDataPoint]:
        """Retrieves snapshot values for all registered tags with error isolation per tag."""
        snapshots = {}
        for tag_name in self.configured_tags.keys():
            try:
                snapshots[tag_name] = self.get_snapshot(tag_name)
            except Exception as e:
                logger.error(f"Failed to retrieve snapshot for {tag_name}: {str(e)}")
                # Provide empty/error data point rather than crashing entire batch
                snapshots[tag_name] = PIDataPoint(
                    timestamp=None,
                    value=f"Error: {str(e)}",
                    Good=False,
                    tag_name=tag_name
                )
        return snapshots

    def get_historical_data(
        self,
        tag_name: str,
        start_time: str = "*-2h",
        end_time: str = "*",
        max_count: int = 100
    ) -> List[PIDataPoint]:
        """
        Retrieves historical recorded time-series telemetry for a specific tag.
        """
        tag = self.get_tag_definition(tag_name)
        if not tag:
            raise PINotFoundError(f"Tag '{tag_name}' is not registered in tags_config.json")

        web_id = tag.web_id or f"MOCK_{tag_name}"
        try:
            stream_resp = self.client.get_stream_recorded(
                web_id=web_id,
                start_time=start_time,
                end_time=end_time,
                max_count=max_count,
                tag_name=tag_name
            )
            for item in stream_resp.items:
                item.tag_name = tag_name
                if not item.units_abbreviation and tag:
                    item.units_abbreviation = tag.engineering_units
            return stream_resp.items
        except PIException as e:
            logger.error(f"Historical query failed for '{tag_name}': {str(e)}")
            raise
