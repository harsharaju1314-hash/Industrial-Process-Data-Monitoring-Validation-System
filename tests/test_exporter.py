"""
Unit Tests for Console Reporter and File Exporter.
"""
from pathlib import Path
import json
import csv
from datetime import datetime, timezone

from src.models.tag_definition import PITag
from src.models.data_point import PIDataPoint
from src.validation.validator import IndustrialDataValidator
from src.reporting.reporter import ConsoleReporter
from src.reporting.exporter import DataExporter


def test_console_reporter(sample_tag_temp, validator):
    reporter = ConsoleReporter()
    points = [PIDataPoint(timestamp=datetime.now(timezone.utc), value=65.0, Good=True)]
    summary = validator.validate_batch(
        {sample_tag_temp.tag_name: points},
        {sample_tag_temp.tag_name: sample_tag_temp},
        is_mock_mode=True
    )
    # Ensure reporting executes without exception
    reporter.print_batch_summary(summary)


def test_exporter_json_and_csv(sample_tag_temp, validator, tmp_path):
    exporter = DataExporter(output_dir=tmp_path)
    points = [
        PIDataPoint(timestamp=datetime.now(timezone.utc), value=102.0, Good=True), # HiHi alarm
        PIDataPoint(timestamp=datetime.now(timezone.utc), value=65.0, Good=True)
    ]
    summary = validator.validate_batch(
        {sample_tag_temp.tag_name: points},
        {sample_tag_temp.tag_name: sample_tag_temp},
        is_mock_mode=True
    )

    # 1. Test JSON Export
    json_path = exporter.export_to_json(summary, filename="test_summary.json")
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_tags_evaluated"] == 1
        assert "REACTOR_01_TEMP" in data["tag_reports"]

    # 2. Test CSV Export
    csv_path = exporter.export_anomalies_to_csv(summary, filename="test_anomalies.csv")
    assert csv_path.exists()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) >= 1
        assert rows[0]["tag_name"] == "REACTOR_01_TEMP"
        assert rows[0]["anomaly_type"] == "OUT_OF_LIMITS_HIHI"
