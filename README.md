# Industrial Process Data Monitoring & Validation System

An engineering-grade, maintainable Python application designed to ingest real-time snapshot and historical time-series process data from **AVEVA OSIsoft PI Data Archive / PI Asset Framework (AF)** via **PI Web API**, validate telemetry data quality, identify bad digital states, detect out-of-limits excursions, flag sensor flatlines, and generate compliance audit reports.

---

## Table of Contents
1. [Project Overview & Use Case](#project-overview--use-case)
2. [Key Features](#key-features)
3. [Architecture & Design Principles](#architecture--design-principles)
4. [Project Structure](#project-structure)
5. [AVEVA PI Web API Integration](#aveva-pi-web-api-integration)
6. [Data Validation Taxonomy](#data-validation-taxonomy)
7. [Installation & Setup](#installation--setup)
8. [Execution Guide (CLI & Streamlit UI)](#execution-guide-cli--streamlit-ui)
9. [Automated Testing Suite (Pytest)](#automated-testing-suite-pytest)
10. [Error Handling & Troubleshooting](#error-handling--troubleshooting)
11. [Live PI vs Simulation Mode Disclaimer](#live-pi-vs-simulation-mode-disclaimer)
12. [Interview Preparation Guide (60s Pitch, 2-Min Deep Dive, Q&A)](#interview-preparation-guide)

---

## Project Overview & Use Case

In continuous process industries (such as oil refining, chemical processing, thermal power generation, and water treatment), supervisory systems stream telemetry from thousands of field transmitters (temperature, pressure, vibration, flow, level) into **AVEVA OSIsoft PI Data Archive**.

Raw telemetry frequently suffers from:
- Field transmitter failure or calibration drift
- Broken wire / communication card faults (resulting in PI System Digital States such as `Bad Input`, `Pt Created`, `Shutdown`, `No Data`)
- Intermittent network dropouts leading to missing/null values
- Historian buffer duplicates
- Unsafe operating limit excursions (LoLo, Lo, Hi, HiHi)
- Sensor freezing / flatlining

This application provides an automated ingestion and validation pipeline that retrieves PI Point telemetry via standard **PI Web API REST endpoints**, evaluates readings against industrial data quality rules, and presents the actionable diagnostics via a Rich CLI and an interactive Streamlit dashboard.

---

## Key Features

- **Dual-Mode Connectivity**: Seamlessly switches between **Live AVEVA PI Web API** (via Basic or Windows Authentication) and a **Local High-Fidelity Simulator** generating authentic industrial anomalies and digital states.
- **Real-Time & Historical Ingestion**: Supports snapshot polling (`/streams/{webId}/value`) and historical time-range queries (`/streams/{webId}/recorded` with PI time syntax e.g. `*-2h` to `*`).
- **4-Tier Operational Alarm Validation**: Evaluates telemetry against configured Low-Low (LoLo), Low (Lo), High (Hi), and High-High (HiHi) limits with severity-graded alerting.
- **Digital State & Quality Flag Detection**: Detects `Good == False` flags and standard PI digital states (`Bad Input`, `Pt Created`, `Shutdown`, `No Data`, `Scan Off`).
- **Multi-Point Time-Series Analytics**:
  - Duplicate timestamp detection
  - Sudden rate-of-change (RoC) jump detection (transmitter electrical noise/spikes)
  - Sensor flatline / freeze detection
- **Comprehensive Audit Trail Reporting**: Outputs colored tabular terminal summaries and exports structured JSON audits and flat CSV anomaly logs.
- **Interactive Streamlit Web Dashboard**: Real-time snapshot cards, interactive historical trend line charts with limit threshold overlays, and searchable anomaly audit tables.
- **Unit & Integration Test Suite**: 30 automated Pytest test cases validating client endpoints, exceptions, validation rules, reporting, and CLI commands.

---

## Architecture & Design Principles

The application adheres to **Clean Architecture** and **SOLID principles**, with strict separation of concerns across layers:

```
+-----------------------------------------------------------------------------------+
|                                 Presentation Layer                                 |
|          Streamlit Web Dashboard (src/ui)     |     CLI Runner (main.py)         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                  Service Layer                                    |
|          PIDataService (src/retrieval)        |     ConsoleReporter / Exporter     |
+-----------------------------------------------------------------------------------+
             |                                                  |
             v                                                  v
+------------------------------------+          +-----------------------------------+
|         Client / Integration       |          |         Validation Engine         |
|   - PIWebApiClient (src/client)    |          |   - IndustrialDataValidator       |
|   - PIAuthHandler (src/client)     |          |   - Atomic & Time-Series Rules    |
|   - Custom PI Exceptions           |          |   - Data Quality Scoring          |
+------------------------------------+          +-----------------------------------+
             |                                                  |
             +-------------------> Models Layer <---------------+
                               (src/models)
                 - PITag & TagLimitConfig
                 - PIDataPoint & DigitalState
                 - ValidationAnomaly & TagValidationReport
```

---

## Project Structure

```
industrial-data-validator/
¦
+-- config/
¦   +-- __init__.py
¦   +-- settings.py              # Environment variable loader (.env) & config constants
¦   +-- tags_config.json         # Tag metadata, engineering units, and 4-tier limits
¦
+-- src/
¦   +-- __init__.py
¦   +-- client/
¦   ¦   +-- __init__.py
¦   ¦   +-- auth.py              # Basic & Windows auth handler for PI Web API
¦   ¦   +-- exceptions.py        # Custom exception hierarchy (PIConnectionError, etc.)
¦   ¦   +-- pi_client.py         # REST client for PI Web API endpoints + simulator fallback
¦   ¦
¦   +-- models/
¦   ¦   +-- __init__.py
¦   ¦   +-- data_point.py        # PIDataPoint, StreamResponse, DigitalState Pydantic models
¦   ¦   +-- tag_definition.py    # PITag metadata and TagLimitConfig definitions
¦   ¦   +-- validation_result.py # ValidationAnomaly, TagValidationReport, BatchValidationSummary
¦   ¦
¦   +-- retrieval/
¦   ¦   +-- __init__.py
¦   ¦   +-- data_service.py      # High-level snapshot & historical time-series service
¦   ¦
¦   +-- validation/
¦   ¦   +-- __init__.py
¦   ¦   +-- rules.py             # Atomic rules (Missing, DigitalState, Limits, RoC, Flatline)
¦   ¦   +-- validator.py         # IndustrialDataValidator engine & quality score calculator
¦   ¦
¦   +-- reporting/
¦   ¦   +-- __init__.py
¦   ¦   +-- reporter.py          # Rich terminal summary & colored table formatter
¦   ¦   +-- exporter.py          # JSON and CSV compliance report generator
¦   ¦
¦   +-- ui/
¦       +-- __init__.py
¦       +-- app.py               # Streamlit interactive UI application
¦
+-- sample_data/
¦   +-- simulated_pi_payloads.json # Authentic AVEVA PI Web API sample response schemas
¦
+-- tests/
¦   +-- __init__.py
¦   +-- conftest.py              # Pytest fixtures and test tags
¦   +-- test_auth.py             # Authentication & header tests
¦   +-- test_pi_client.py        # HTTP client, status codes (401, 404, 500), and mock tests
¦   +-- test_data_service.py     # Data service layer snapshot & historical query tests
¦   +-- test_validator.py        # Complete validation rule coverage tests
¦   +-- test_exporter.py         # Console reporter, JSON and CSV export tests
¦   +-- test_cli.py              # CLI subprocess integration tests
¦
+-- reports/                     # Output directory for exported JSON and CSV reports
¦   +-- .gitkeep
¦
+-- .env.example                 # Template for PI server connection configuration
+-- .gitignore                   # Standard Python/IDE ignore rules
+-- main.py                      # CLI entrypoint
+-- pyproject.toml               # Project build metadata and pytest configuration
+-- requirements.txt             # Direct Python dependencies
+-- README.md                    # System documentation and interview guide
```

---

## AVEVA PI Web API Integration

The application interfaces with standard AVEVA OSIsoft PI Web API REST endpoints:

| Endpoint | Method | Purpose | Implementation File |
| :--- | :--- | :--- | :--- |
| `/dataservers?name={name}` | `GET` | Verifies connection and retrieves Data Server metadata | `src/client/pi_client.py:test_connection` |
| `/points?path=\\SERVER\TAG` | `GET` | Resolves PI Point path to WebID and metadata | `src/client/pi_client.py:get_point_by_path` |
| `/streams/{webId}/value` | `GET` | Retrieves current snapshot reading for a PI Point | `src/client/pi_client.py:get_stream_value` |
| `/streams/{webId}/recorded` | `GET` | Ingests recorded historical time-series data (`startTime`, `endTime`, `maxCount`) | `src/client/pi_client.py:get_stream_recorded` |

### Supported Authentication Methods:
- **Mock / Simulation Mode**: Offline testing with realistic telemetry generation (default).
- **Basic Authentication**: `HTTPBasicAuth(username, password)` with `X-Requested-With: XMLHttpRequest` header.
- **Windows / Kerberos / NTLM**: Configured via corporate intranet proxy or session headers.

---

## Data Validation Taxonomy

The system runs 7 distinct validation checks against ingested data points:

```
Ingested PI Point
   +-- [Check 1] Null / Missing Check --> Value is None or Timestamp missing? --> [MISSING_VALUE: ERROR]
   +-- [Check 2] PI Quality Flag & Digital State --> Good == False or Bad State? --> [BAD_DIGITAL_STATE: CRITICAL]
   +-- [Check 3] Data Type Check --> Non-numeric string for Float32 tag? --> [NON_NUMERIC_TYPE: ERROR]
   +-- [Check 4] 4-Tier Operational Limits Check:
   ¦              +-- Value >= HiHi Limit? --> [OUT_OF_LIMITS_HIHI: CRITICAL]
   ¦              +-- Value >= Hi Limit?   --> [OUT_OF_LIMITS_HI: WARNING]
   ¦              +-- Value <= LoLo Limit? --> [OUT_OF_LIMITS_LOLO: CRITICAL]
   ¦              +-- Value <= Lo Limit?   --> [OUT_OF_LIMITS_LO: WARNING]
   +-- [Time-Series Checks (Multi-point)]:
                  +-- Duplicate Timestamps? --> [DUPLICATE_TIMESTAMP: WARNING]
                  +-- Rate of Change Spike?  --> [RATE_OF_CHANGE_SPIKE: WARNING]
                  +-- Sensor Flatline / Freeze (>= N points identical)? --> [SIGNAL_FLATLINE: WARNING]
```

### Configured Process Variables (`config/tags_config.json`):
1. **`REACTOR_01_TEMP`** (degC): Core Temperature (Target: 65.0, LoLo: 10.0, Lo: 20.0, Hi: 85.0, HiHi: 95.0, Max RoC: 5.0 degC/min)
2. **`REACTOR_01_PRESS`** (bar): Vessel Pressure (Target: 3.5, LoLo: 0.5, Lo: 1.0, Hi: 6.0, HiHi: 8.0, Max RoC: 1.5 bar/min)
3. **`COOLING_PUMP_FLOW`** (m3/h): Secondary Cooling Flow (Target: 35.0, LoLo: 5.0, Lo: 10.0, Hi: 50.0, HiHi: 60.0, Max RoC: 10.0 m3/h/min)
4. **`COMPRESSOR_VIBRATION`** (mm/s): Bearing Vibration (Target: 2.2, LoLo: 0.0, Lo: 0.5, Hi: 4.5, HiHi: 7.0, Max RoC: 2.0 mm/s/min)
5. **`STORAGE_TANK_LEVEL`** (%): Chemical Tank Level (Target: 50.0, LoLo: 5.0, Lo: 15.0, Hi: 85.0, HiHi: 95.0, Max RoC: 5.0 %/min)

---

## Installation & Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/harsharaju1314-hash/Industrial-Process-Data-Monitoring-Validation-System.git
cd Industrial-Process-Data-Monitoring-Validation-System
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (.env)
Copy `.env.example` to `.env` (optional when running in default mock/simulation mode):
```bash
cp .env.example .env
```

---

## Execution Guide (CLI & Streamlit UI)

### 1. Command-Line Interface (CLI)

#### Run Batch Historical Time-Series Validation (Default)
```bash
python main.py --mode batch-historical --export-format all
```

#### Run Real-Time Snapshot Validation
```bash
python main.py --mode snapshot
```

#### Query Specific Tag with Custom Time Range
```bash
python main.py --mode historical --tag "REACTOR_01_TEMP" --start-time "*-4h" --end-time "*" --max-count 100 --export-format json
```

#### Test Live PI Web API Connection
```bash
python main.py --mode test-connection
```

### 2. Streamlit Web Dashboard

Launch the interactive web UI:
```bash
streamlit run src/ui/app.py
```
Open your browser to `http://localhost:8501` to view:
- **Real-Time Snapshot Tab**: Live status badges and process variables against target setpoints.
- **Historical Telemetry Tab**: Interactive time-series trend line charts with Hi/HiHi/Lo/LoLo limit lines.
- **Anomaly Audit Tab**: Filterable table of all detected anomalies with root-cause messages and recommended remediations.
- **Export Reports Tab**: One-click download of JSON compliance audits and CSV anomaly tables.

---

## Automated Testing Suite (Pytest)

The project includes **30 unit and integration tests** verifying all modules:

```bash
pytest -v tests/
```

### Test Coverage Summary:
- **`test_auth.py`**: Authentication headers, basic auth credentials object, mock mode handler.
- **`test_pi_client.py`**: Connection test, point by path, snapshot stream, recorded historical stream, HTTP 401 Unauthorized handling, HTTP 404 Not Found handling, HTTP 500 Server Error handling.
- **`test_data_service.py`**: Tag configuration loading, snapshot retrieval, batch snapshots, historical queries, unknown tag exception.
- **`test_validator.py`**: Valid point acceptance, missing value detection, PI Digital State detection (`Bad Input`, `Shutdown`), non-numeric data type checks, 4-tier limits (LoLo, Lo, Hi, HiHi), duplicate timestamp detection, rate of change spike detection, sensor flatline detection, full time-series report quality score calculation.
- **`test_exporter.py`**: Rich console output formatting, JSON audit file export, CSV anomaly export.
- **`test_cli.py`**: `--help`, `--mode test-connection`, `--mode snapshot`, and `--mode historical` CLI executions.

---

## Error Handling & Troubleshooting

| Error Symptom | Root Cause | System Behavior & Troubleshooting |
| :--- | :--- | :--- |
| `PIAuthenticationError (HTTP 401/403)` | Invalid username/password or insufficient PI AF/Data Archive ACL permissions | Custom exception raised with remediation prompt to verify credentials or check PI mapping in PI SMT. |
| `PINotFoundError (HTTP 404)` | Tag name misspelled or WebID does not exist on target Data Server | Custom exception caught, descriptive log created, tag highlighted as missing in validation report. |
| `PITimeoutError / ConnectionError` | PI Web API service stopped, firewall blocking port 443/5450, or DNS failure | Timeout caught after configured `PI_TIMEOUT_SECONDS`; fallback to simulator or clean exit without unhandled crash. |
| `BAD_DIGITAL_STATE ('Bad Input')` | Field sensor disconnect, broken RTD wire, or DCS card glitch | Data Point marked invalid (`Good: false`), CRITICAL severity anomaly flagged with prompt to inspect field wiring. |
| `SIGNAL_FLATLINE` | Transmitter sensing line blocked or sensor ADC converter stuck | Multi-point rule flags warning when $\ge N$ points have variance $\le$ tolerance threshold. |

---

## Live PI vs Simulation Mode Disclaimer

- **What runs in Simulation Mode**:
  - Realistic time-series generation with authentic PI System Digital States (`Bad Input`, `Pt Created`, `Shutdown`), noise drift, limit excursions, and flatlines.
  - Full local execution of the validation engine, reporting, CSV/JSON export, Pytest suite, and Streamlit UI without requiring a commercial AVEVA license.
- **What connects to a Live PI Server**:
  - Setting `PI_AUTH_MODE=basic` and providing a valid `PI_WEB_API_URL` connects directly to commercial AVEVA OSIsoft PI Web API instances using standard HTTPS REST calls.

---

## Interview Preparation Guide

### 60-Second Project Pitch
> *"I built an Industrial Process Data Monitoring and Validation System in Python for AVEVA OSIsoft PI. The system connects to the PI Data Archive via PI Web API using standard REST endpoints like `/streams/{webId}/recorded`. It ingests real-time and historical sensor telemetry from process equipment like reactors and compressors, and runs a modular validation engine that flags bad PI digital states, missing readings, out-of-bounds operational alarms—such as Low-Low and High-High limits—rate-of-change spikes, and sensor flatlines. It features both a Rich terminal CLI with CSV/JSON audit export and a Streamlit dashboard. The entire project is covered by 30 Pytest unit and integration tests and is built to cleanly handle both live PI Web API servers and offline simulation testing."*

### 2-Minute Technical Deep Dive
> *"In industrial environments, data ingested into the PI Data Archive often suffers from sensor disconnects, communication faults, or unsafe process excursions. I designed this system with clean separation of concerns:
> 1. **Client Layer (`PIWebApiClient` & `PIAuthHandler`)**: Interacts with PI Web API REST endpoints using requests and Pydantic models. It handles authentication, CSRF tokens via standard headers, and translates HTTP error codes into custom domain exceptions like `PIAuthenticationError` and `PINotFoundError`. It also includes a high-fidelity simulator for offline verification.
> 2. **Service Layer (`PIDataService`)**: Manages tag registries loaded from JSON configuration, resolves WebIDs, and queries snapshot or time-range streams using relative PI time formats like `*-2h`.
> 3. **Validation Engine (`IndustrialDataValidator`)**: Uses modular rules to evaluate points against 4-tier limits—LoLo, Lo, Hi, HiHi—detects PI digital state errors like `Bad Input` and `Pt Created`, and runs multi-point time-series algorithms to identify duplicate timestamps, rate-of-change spikes, and sensor flatlines.
> 4. **Presentation & Reporting**: Provides a Streamlit UI for visual trend analysis with limit thresholds, a Rich console reporter, and automated JSON/CSV exporters for compliance audit trails.
> 5. **Testing**: The codebase has 30 Pytest tests covering error handling, HTTP failure simulations, validation algorithms, and CLI subprocess execution."*

### Common Interview Q&A

**Q1: How does PI Web API differ from PI SDK or AF SDK?**
*Answer*: PI SDK is a legacy COM-based library, and AF SDK is a .NET library requiring Windows. PI Web API is a modern, platform-independent RESTful interface that allows any language (like Python) running on any operating system to read and write PI data over standard HTTPS using JSON.

**Q2: How do you handle PI Digital States versus numeric process values?**
*Answer*: In PI, when a sensor fails, the value field does not contain a float; instead, it returns a Digital State object (like `Bad Input` or `Shutdown`) with `Good == False`. In my application, the `PIDataPoint` model inspects whether the payload is numeric or a digital state dictionary, allowing the validation engine to raise specific `BAD_DIGITAL_STATE` anomalies with appropriate remediation advice.

**Q3: How do you test the application without a 24/7 connection to a production PI server?**
*Answer*: I implemented a dual-mode client architecture. When configured with a live server URL and credentials, it communicates over HTTPS REST. When running offline or during testing, it uses a high-fidelity simulation engine that returns schemas identical to real AVEVA PI Web API endpoints, including authentic anomalies and digital states. In Pytest, we also test HTTP 401, 404, and 500 error scenarios using mock responses.

---

## Resume Bullets (Accurate & Feature-Verified)

- *Developed a Python-based Industrial Process Data Monitoring and Validation System integrating with AVEVA OSIsoft PI Web API to ingest real-time and historical time-series sensor telemetry.*
- *Engineered a modular validation engine to detect PI System Digital States (`Bad Input`, `Shutdown`), missing data, 4-tier operational limit breaches (LoLo, Lo, Hi, HiHi), rate-of-change spikes, and sensor flatlines.*
- *Implemented RESTful client abstraction with custom exception hierarchy (`PIConnectionError`, `PIAuthenticationError`), supporting Basic/Windows authentication and automated JSON/CSV audit trail generation.*
- *Built an interactive Streamlit monitoring dashboard for process trend visualization, limit threshold overlays, and real-time anomaly diagnostics.*
- *Authored a comprehensive test suite of 30 Pytest unit and integration tests covering API error handling, validation algorithms, and CLI execution.*

---

## Technologies Used
- **Language**: Python 3.12
- **Industrial Historian Interface**: AVEVA OSIsoft PI Web API (REST)
- **Data Modeling & Validation**: Pydantic v2
- **Testing**: Pytest
- **Data Analysis**: Pandas
- **Visualization / UI**: Streamlit, Rich
- **Version Control**: Git & GitHub
