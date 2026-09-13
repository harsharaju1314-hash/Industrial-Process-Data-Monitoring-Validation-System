"""
Terminal Console Reporter for Industrial Data Validation.
Outputs clean, formatted validation tables and quality metrics using Rich (with ASCII fallback).
"""
import sys
from typing import Dict
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from src.models.validation_result import (
    BatchValidationSummary,
    TagValidationReport,
    ValidationSeverity
)


class ConsoleReporter:
    """Renders formatted industrial validation summaries to the console."""

    def __init__(self):
        self.console = Console() if HAS_RICH else None

    def print_batch_summary(self, summary: BatchValidationSummary):
        """Prints high-level batch summary card and per-tag validation metrics."""
        if HAS_RICH:
            self._print_rich_summary(summary)
        else:
            self._print_plain_summary(summary)

    def _print_rich_summary(self, summary: BatchValidationSummary):
        title = f"[bold cyan]INDUSTRIAL PROCESS DATA VALIDATION REPORT[/bold cyan] (Mode: [yellow]{summary.mode}[/yellow])"
        status_color = "green" if summary.overall_quality_score >= 90 else ("yellow" if summary.overall_quality_score >= 75 else "red")
        
        summary_text = (
            f"Execution Time: [bold]{summary.execution_time.strftime('%Y-%m-%d %H:%M:%S UTC')}[/bold]\n"
            f"Total Tags Evaluated: [bold]{summary.total_tags_evaluated}[/bold] | "
            f"Total Data Points: [bold]{summary.total_data_points}[/bold] | "
            f"Total Anomalies: [bold red]{summary.total_anomalies_detected}[/bold red]\n"
            f"Overall Data Quality Score: [bold {status_color}]{summary.overall_quality_score}%[/bold {status_color}]"
        )
        self.console.print(Panel(summary_text, title=title, border_style="cyan", box=box.ROUNDED))

        table = Table(title="[bold]Tag Quality Summary[/bold]", box=box.SIMPLE_HEAVY)
        table.add_column("Tag Name", style="bold white")
        table.add_column("Units", style="cyan")
        table.add_column("Total Pts", justify="right")
        table.add_column("Valid Pts", justify="right", style="green")
        table.add_column("Missing", justify="right", style="magenta")
        table.add_column("Bad State", justify="right", style="red")
        table.add_column("Out of Limit", justify="right", style="yellow")
        table.add_column("Quality Score", justify="right", style="bold")
        table.add_column("Health", justify="center")

        for tag_name, rep in summary.tag_reports.items():
            health_badge = "Healthy" if rep.status_summary == "HEALTHY" else ("Warning" if rep.status_summary == "WARNING" else "Critical")
            score_style = "green" if rep.data_quality_score >= 90 else ("yellow" if rep.data_quality_score >= 75 else "red")
            
            table.add_row(
                rep.tag_name,
                rep.engineering_units,
                str(rep.total_points_evaluated),
                str(rep.valid_points_count),
                str(rep.missing_points_count),
                str(rep.bad_state_points_count),
                str(rep.out_of_limits_count),
                f"[{score_style}]{rep.data_quality_score}%[/{score_style}]",
                health_badge
            )
        self.console.print(table)

        anomalies_found = []
        for rep in summary.tag_reports.values():
            anomalies_found.extend(rep.anomalies)

        if anomalies_found:
            anom_table = Table(title="[bold red]Detected Telemetry & Operational Anomalies[/bold red]", box=box.SIMPLE)
            anom_table.add_column("Tag", style="bold")
            anom_table.add_column("Timestamp", style="dim")
            anom_table.add_column("Severity", justify="center")
            anom_table.add_column("Type", style="cyan")
            anom_table.add_column("Observed", style="yellow")
            anom_table.add_column("Root Cause Message")
            anom_table.add_column("Suggested Remediation", style="green")

            for a in anomalies_found[:15]:
                sev_color = "red" if a.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.ERROR) else "yellow"
                ts_str = a.timestamp.strftime("%H:%M:%S") if a.timestamp else "N/A"
                anom_table.add_row(
                    a.tag_name,
                    ts_str,
                    f"[{sev_color}]{a.severity.value}[/{sev_color}]",
                    a.anomaly_type.value,
                    str(a.observed_value),
                    a.message,
                    a.suggested_action
                )
            self.console.print(anom_table)
            if len(anomalies_found) > 15:
                self.console.print(f"[dim]... and {len(anomalies_found) - 15} more anomalies (see exported report)[/dim]")

    def _print_plain_summary(self, summary: BatchValidationSummary):
        print("=" * 80)
        print(f"INDUSTRIAL PROCESS DATA VALIDATION REPORT (Mode: {summary.mode})")
        print(f"Time: {summary.execution_time.isoformat()} | Quality Score: {summary.overall_quality_score}%")
        print(f"Tags: {summary.total_tags_evaluated} | Total Points: {summary.total_data_points} | Anomalies: {summary.total_anomalies_detected}")
        print("=" * 80)
        print(f"{'Tag Name':<25} {'Total':<8} {'Valid':<8} {'Bad/Miss':<10} {'OutLimit':<10} {'Quality %':<10} {'Status'}")
        print("-" * 80)
        for tag_name, rep in summary.tag_reports.items():
            bad_or_miss = rep.missing_points_count + rep.bad_state_points_count
            print(f"{rep.tag_name:<25} {rep.total_points_evaluated:<8} {rep.valid_points_count:<8} {bad_or_miss:<10} {rep.out_of_limits_count:<10} {rep.data_quality_score:<10} {rep.status_summary}")
        print("=" * 80)
