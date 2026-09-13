"""
Integration Tests for CLI Entrypoint (main.py).
"""
import subprocess
import sys
import pytest


def test_cli_help():
    result = subprocess.run([sys.executable, "main.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "AVEVA OSIsoft PI Industrial Process Data Monitoring" in result.stdout


def test_cli_test_connection_mock():
    result = subprocess.run([sys.executable, "main.py", "--mode", "test-connection", "--force-mock"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "CONNECTED_SIMULATED" in result.stdout


def test_cli_snapshot_mode():
    result = subprocess.run([sys.executable, "main.py", "--mode", "snapshot", "--export-format", "none", "--force-mock"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "INDUSTRIAL PROCESS DATA VALIDATION REPORT" in result.stdout


def test_cli_historical_single_tag():
    result = subprocess.run([sys.executable, "main.py", "--mode", "historical", "--tag", "REACTOR_01_TEMP", "--max-count", "20", "--export-format", "none", "--force-mock"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "INDUSTRIAL PROCESS DATA VALIDATION REPORT" in result.stdout
