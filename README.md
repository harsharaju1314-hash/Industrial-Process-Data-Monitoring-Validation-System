# Industrial Process Data Monitoring & Validation System

A Python application for ingesting, validating, and monitoring industrial time-series telemetry from **AVEVA OSIsoft PI** via **PI Web API**.

The system monitors process variables (temperature, pressure, flow, vibration, level), validates data quality against engineering limits and PI digital states, and presents findings through a CLI tool, exportable reports (JSON/CSV), and a Streamlit dashboard.

---

## Features

- **AVEVA PI Web API Integration**: Ingests snapshot (`/streams/{webId}/value`) and historical time-series (`/streams/{webId}/recorded`) data.
- **Dual Mode**: Connects to a live PI Web API server or runs in local simulation mode for offline development and testing.
- **Data Validation Engine**:
  - Detects missing/null telemetry readings.
  - Identifies PI System digital state errors (`Bad Input`, `Shutdown`, `Pt Created`, `Good: false`).
  - Flags 4-tier operational limit breaches: Low-Low (`LoLo`), Low (`Lo`), High (`Hi`), and High-High (`HiHi`).
  - Detects time-series anomalies: duplicate timestamps, rate-of-change spikes, and sensor flatlines.
- **Quality Scoring**: Computes percentage-based data quality metrics per tag and across batches.
- **Reporting & UI**:
  - Rich terminal console output.
  - Audit export to JSON and CSV formats.
  - Interactive Streamlit dashboard with time-series charts and threshold overlays.
- **Automated Tests**: 30 Pytest unit and integration tests.

---

## Project Structure

```
industrial-data-validator/
+-- config/
¦   +-- settings.py              # Environment and app configuration
¦   +-- tags_config.json         # Tag metadata, engineering units & alarm limits
+-- src/
¦   +-- client/
¦   ¦   +-- auth.py              # Authentication handler (Basic, Windows, Mock)
¦   ¦   +-- exceptions.py        # Custom PI domain exceptions
¦   ¦   +-- pi_client.py         # PI Web API REST client & simulation fallback
¦   +-- models/
¦   ¦   +-- data_point.py        # PIDataPoint and StreamResponse models
¦   ¦   +-- tag_definition.py    # PITag and TagLimitConfig definitions
¦   ¦   +-- validation_result.py # Anomaly, report, and summary models
¦   +-- retrieval/
¦   ¦   +-- data_service.py      # Snapshot and historical retrieval service
¦   +-- validation/
¦   ¦   +-- rules.py             # Atomic & time-series validation rules
¦   ¦   +-- validator.py         # IndustrialDataValidator engine
¦   +-- reporting/
¦   ¦   +-- reporter.py          # Terminal output formatting
¦   ¦   +-- exporter.py          # JSON and CSV report generation
¦   +-- ui/
¦       +-- app.py               # Streamlit web dashboard
+-- sample_data/
¦   +-- simulated_pi_payloads.json # Sample PI Web API payload schemas
+-- tests/
¦   +-- conftest.py              # Pytest fixtures
¦   +-- test_auth.py             # Auth tests
¦   +-- test_pi_client.py        # PI client & HTTP error tests
¦   +-- test_data_service.py     # Retrieval service tests
¦   +-- test_validator.py        # Validation rule tests
¦   +-- test_exporter.py         # Exporter tests
¦   +-- test_cli.py              # CLI integration tests
+-- reports/                     # Output directory for exported reports
+-- .env.example                 # Environment variable template
+-- main.py                      # CLI entrypoint
+-- pyproject.toml
+-- requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/harsharaju1314-hash/Industrial-Process-Data-Monitoring-Validation-System.git
   cd Industrial-Process-Data-Monitoring-Validation-System
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional for live PI)**:
   ```bash
   cp .env.example .env
   ```
   *By default, `PI_AUTH_MODE=mock` is enabled, allowing full offline testing without a live PI server.*

---

## Usage

### 1. CLI

- **Run batch historical validation across all configured tags**:
  ```bash
  python main.py --mode batch-historical --export-format all
  ```

- **Run real-time snapshot validation**:
  ```bash
  python main.py --mode snapshot
  ```

- **Query a specific tag with custom time range**:
  ```bash
  python main.py --mode historical --tag "REACTOR_01_TEMP" --start-time "*-2h" --end-time "*" --max-count 50
  ```

- **Test connection to PI Web API**:
  ```bash
  python main.py --mode test-connection
  ```

### 2. Streamlit Dashboard

Launch the interactive dashboard:
```bash
streamlit run src/ui/app.py
```

Features:
- **Snapshot View**: Real-time readings, target setpoints, and status indicators.
- **Historical Trends**: Interactive charts showing sensor telemetry alongside HiHi, Hi, Lo, and LoLo operational limit lines.
- **Anomaly Log**: Searchable table of detected anomalies with root-cause messages and suggested remediations.
- **Report Export**: Download validation results as JSON or CSV directly from the browser.

---

## Running Tests

Run the full Pytest suite:

```bash
pytest -v tests/
```

All 30 unit and integration tests cover:
- Authentication and request header generation
- REST client endpoints and HTTP error handling (401, 404, 500, timeouts)
- Data retrieval and tag resolution
- Missing data, bad digital states, and data type validation
- 4-tier operational limits (LoLo, Lo, Hi, HiHi)
- Duplicate timestamps, rate-of-change spikes, and sensor flatlines
- Report generation, JSON/CSV exports, and CLI execution

---

## Monitored Process Variables

Configured in `config/tags_config.json`:

| Tag Name | Description | Units | Target | LoLo / Lo | Hi / HiHi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `REACTOR_01_TEMP` | Reactor Core Temperature | degC | 65.0 | 10.0 / 20.0 | 85.0 / 95.0 |
| `REACTOR_01_PRESS` | Vessel Internal Pressure | bar | 3.5 | 0.5 / 1.0 | 6.0 / 8.0 |
| `COOLING_PUMP_FLOW` | Secondary Cooling Water Flow | m3/h | 35.0 | 5.0 / 10.0 | 50.0 / 60.0 |
| `COMPRESSOR_VIBRATION`| Bearing Vibration Velocity | mm/s | 2.2 | 0.0 / 0.5 | 4.5 / 7.0 |
| `STORAGE_TANK_LEVEL` | Chemical Storage Tank Level | % | 50.0 | 5.0 / 15.0 | 85.0 / 95.0 |

---

## License

MIT License.
