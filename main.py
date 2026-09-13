"""
Industrial Process Data Monitoring & Validation System CLI.
Command-line interface for running snapshot validations, historical evaluations, and automated audit exports.
"""
import argparse
import sys
import logging
from datetime import datetime

from config.settings import settings
from src.client.pi_client import PIWebApiClient
from src.client.exceptions import PIException
from src.retrieval.data_service import PIDataService
from src.validation.validator import IndustrialDataValidator
from src.reporting.reporter import ConsoleReporter
from src.reporting.exporter import DataExporter

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("IndustrialDataValidator")


def main():
    parser = argparse.ArgumentParser(
        description="AVEVA OSIsoft PI Industrial Process Data Monitoring & Validation System"
    )
    parser.add_argument(
        "--mode",
        choices=["snapshot", "historical", "batch-historical", "test-connection"],
        default="batch-historical",
        help="Execution mode: 'snapshot', 'historical', 'batch-historical', or 'test-connection'"
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="REACTOR_01_TEMP",
        help="PI Tag name to query (for 'historical' mode)"
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default="*-2h",
        help="PI relative/absolute start time (e.g., '*-2h')"
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default="*",
        help="PI relative/absolute end time (e.g., '*')"
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=50,
        help="Maximum number of historical points to retrieve per tag"
    )
    parser.add_argument(
        "--export-format",
        choices=["json", "csv", "all", "none"],
        default="json",
        help="Format to export validation results ('json', 'csv', 'all', 'none')"
    )
    parser.add_argument(
        "--force-mock",
        action="store_true",
        help="Force simulation mode even if live PI URL is configured in .env"
    )

    args = parser.parse_args()

    client = PIWebApiClient(force_mock=args.force_mock)
    service = PIDataService(client=client)
    validator = IndustrialDataValidator()
    reporter = ConsoleReporter()
    exporter = DataExporter()

    if args.mode == "test-connection":
        try:
            res = client.test_connection()
            print(f"PI Web API Connection Test Result: {res}")
            sys.exit(0)
        except PIException as e:
            logger.error(f"Connection test failed: {str(e)}")
            sys.exit(1)

    if args.mode == "snapshot":
        logger.info("Executing real-time snapshot validation for configured tags...")
        snapshots = service.get_all_snapshots()
        telemetry_map = {tag_name: [point] for tag_name, point in snapshots.items()}
        summary = validator.validate_batch(telemetry_map, service.configured_tags, is_mock_mode=client.is_mock)
        reporter.print_batch_summary(summary)

    elif args.mode == "historical":
        logger.info(f"Querying historical telemetry for tag '{args.tag}' from {args.start_time} to {args.end_time}...")
        tag_def = service.get_tag_definition(args.tag)
        if not tag_def:
            logger.error(f"Tag '{args.tag}' is not found in tags_config.json")
            sys.exit(1)

        points = service.get_historical_data(
            args.tag,
            start_time=args.start_time,
            end_time=args.end_time,
            max_count=args.max_count
        )
        telemetry_map = {args.tag: points}
        summary = validator.validate_batch(telemetry_map, {args.tag: tag_def}, is_mock_mode=client.is_mock)
        reporter.print_batch_summary(summary)

    elif args.mode == "batch-historical":
        logger.info("Executing batch historical time-series validation across all configured tags...")
        telemetry_map = {}
        for tag in service.list_tags():
            try:
                pts = service.get_historical_data(
                    tag.tag_name,
                    start_time=args.start_time,
                    end_time=args.end_time,
                    max_count=args.max_count
                )
                telemetry_map[tag.tag_name] = pts
            except Exception as e:
                logger.error(f"Failed to fetch historical telemetry for {tag.tag_name}: {str(e)}")

        summary = validator.validate_batch(telemetry_map, service.configured_tags, is_mock_mode=client.is_mock)
        reporter.print_batch_summary(summary)

    if args.export_format in ("json", "all"):
        json_file = exporter.export_to_json(summary)
        print(f"Validation JSON Audit exported: {json_file}")
    if args.export_format in ("csv", "all"):
        csv_file = exporter.export_anomalies_to_csv(summary)
        print(f"Validation Anomalies CSV exported: {csv_file}")


if __name__ == "__main__":
    main()
