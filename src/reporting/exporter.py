"""
Data and Validation Audit Trail Exporter.
Saves validation results and telemetry to JSON and CSV formats for compliance and historical tracking.
"""
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import settings
from src.models.validation_result import BatchValidationSummary, TagValidationReport


class DataExporter:
    """Exports validation reports to persistent storage."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_to_json(self, summary: BatchValidationSummary, filename: Optional[str] = None) -> Path:
        """Exports full BatchValidationSummary to a structured JSON file."""
        if not filename:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{ts}.json"

        target_file = self.output_dir / filename
        data = summary.model_dump(mode="json")

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=str)

        return target_file

    def export_anomalies_to_csv(self, summary: BatchValidationSummary, filename: Optional[str] = None) -> Path:
        """Exports all detected anomalies across tags into a flat CSV audit table."""
        if not filename:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_anomalies_{ts}.csv"

        target_file = self.output_dir / filename
        fieldnames = [
            "tag_name",
            "timestamp",
            "severity",
            "anomaly_type",
            "observed_value",
            "threshold_or_rule",
            "message",
            "suggested_action"
        ]

        with open(target_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rep in summary.tag_reports.values():
                for a in rep.anomalies:
                    writer.writerow({
                        "tag_name": a.tag_name,
                        "timestamp": a.timestamp.isoformat() if a.timestamp else "N/A",
                        "severity": a.severity.value,
                        "anomaly_type": a.anomaly_type.value,
                        "observed_value": str(a.observed_value),
                        "threshold_or_rule": a.threshold_or_rule,
                        "message": a.message,
                        "suggested_action": a.suggested_action
                    })

        return target_file
