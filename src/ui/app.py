"""
Industrial Process Data Monitoring & Validation Dashboard.
Streamlit UI for real-time telemetry inspection, threshold tracking, and anomaly visualization.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from config.settings import settings
from src.client.pi_client import PIWebApiClient
from src.retrieval.data_service import PIDataService
from src.validation.validator import IndustrialDataValidator
from src.reporting.exporter import DataExporter

st.set_page_config(
    page_title="Industrial Process Data Validator | AVEVA PI",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("?? Industrial Process Data Monitoring & Validation System")
st.caption("Real-Time Telemetry Integrity & Operational Limits Validation for AVEVA OSIsoft PI / PI Web API")

# Sidebar Configuration
st.sidebar.header("?? PI Web API Configuration")
mock_mode = st.sidebar.toggle("Simulation / Mock Mode", value=True, help="Toggle between Simulated plant data and Live PI Web API")
server_name = st.sidebar.text_input("PI Data Server", value=settings.PI_DATA_SERVER_NAME)
lookback_hours = st.sidebar.slider("Historical Lookback (Hours)", min_value=1, max_value=24, value=2)

client = PIWebApiClient(force_mock=mock_mode)
service = PIDataService(client=client)
validator = IndustrialDataValidator()
exporter = DataExporter()

with st.sidebar.expander("?? Connection Diagnostics", expanded=False):
    try:
        conn = client.test_connection()
        st.success(f"Status: {conn['status']}")
        st.info(f"Server: {conn.get('data_server', server_name)}")
        st.caption(f"Mode: {'Simulated Provider' if conn['is_mock'] else 'Live PI Server'}")
    except Exception as e:
        st.error(f"Connection Failed: {str(e)}")

tab_snapshot, tab_historical, tab_anomalies, tab_export = st.tabs([
    "?? Real-Time Snapshot",
    "?? Historical Telemetry & Trends",
    "?? Anomaly & Quality Audit",
    "?? Export Reports"
])

# -----------------
# Tab 1: Snapshot
# -----------------
with tab_snapshot:
    st.subheader("Current Operational Snapshot")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Monitoring **{len(service.list_tags())}** active industrial process variables.")
    with col2:
        st.button("?? Refresh Data", use_container_width=True)

    tags = service.list_tags()
    cols = st.columns(len(tags))

    snapshot_data = []
    for idx, tag in enumerate(tags):
        point = service.get_snapshot(tag.tag_name)
        validation = validator.validate_point(point, tag)
        val_str = f"{point.numeric_value} {tag.engineering_units}" if point.numeric_value is not None else str(point.value)
        
        with cols[idx % len(cols)]:
            st.metric(
                label=tag.tag_name,
                value=val_str,
                delta=f"Target: {tag.limits.target} {tag.engineering_units}" if tag.limits.target else None
            )
            if validation.is_valid:
                st.caption("?? Status: Normal")
            else:
                st.caption(f"?? Issue: {validation.anomalies[0].anomaly_type.value if validation.anomalies else 'Fault'}")

        snapshot_data.append({
            "Tag Name": tag.tag_name,
            "Description": tag.description,
            "Current Value": point.value,
            "Units": tag.engineering_units,
            "Timestamp (UTC)": point.timestamp.strftime("%Y-%m-%d %H:%M:%S") if point.timestamp else "N/A",
            "PI Quality Good": point.good,
            "Validation Status": "VALID" if validation.is_valid else "INVALID",
            "Issues": ", ".join(a.message for a in validation.anomalies) if validation.anomalies else "None"
        })

    st.markdown("### Snapshot Details Table")
    st.dataframe(pd.DataFrame(snapshot_data), use_container_width=True)

# -----------------
# Tab 2: Historical
# -----------------
with tab_historical:
    st.subheader("Time-Series Process Trends & Operational Limits")
    tag_names = [t.tag_name for t in service.list_tags()]
    selected_tag_name = st.selectbox("Select PI Tag to Analyze", tag_names)
    selected_tag = service.get_tag_definition(selected_tag_name)

    if selected_tag:
        with st.spinner(f"Ingesting time-series telemetry for {selected_tag_name}..."):
            points = service.get_historical_data(
                selected_tag_name,
                start_time=f"*-{lookback_hours}h",
                end_time="*",
                max_count=60
            )
            report = validator.validate_time_series(points, selected_tag)

        chart_df = []
        for p in points:
            if p.timestamp and p.numeric_value is not None:
                row = {
                    "Timestamp": p.timestamp,
                    "Value": p.numeric_value
                }
                if selected_tag.limits.high is not None:
                    row["Hi Limit"] = selected_tag.limits.high
                if selected_tag.limits.high_high is not None:
                    row["HiHi Limit"] = selected_tag.limits.high_high
                if selected_tag.limits.low is not None:
                    row["Lo Limit"] = selected_tag.limits.low
                if selected_tag.limits.low_low is not None:
                    row["LoLo Limit"] = selected_tag.limits.low_low
                chart_df.append(row)

        if chart_df:
            df = pd.DataFrame(chart_df).set_index("Timestamp")
            st.line_chart(df)

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric("Total Points", report.total_points_evaluated)
        mcol2.metric("Valid Points", report.valid_points_count)
        mcol3.metric("Anomalies Found", len(report.anomalies))
        mcol4.metric("Data Quality Score", f"{report.data_quality_score}%")

# -----------------
# Tab 3: Anomalies
# -----------------
with tab_anomalies:
    st.subheader("Detected Telemetry & Operational Anomalies")
    all_telemetry = {}
    for t in service.list_tags():
        pts = service.get_historical_data(t.tag_name, start_time=f"*-{lookback_hours}h", end_time="*", max_count=50)
        all_telemetry[t.tag_name] = pts

    batch_summary = validator.validate_batch(all_telemetry, service.configured_tags, is_mock_mode=mock_mode)

    anom_rows = []
    for rep in batch_summary.tag_reports.values():
        for a in rep.anomalies:
            anom_rows.append({
                "Tag": a.tag_name,
                "Timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.timestamp else "N/A",
                "Severity": a.severity.value,
                "Anomaly Type": a.anomaly_type.value,
                "Observed Value": str(a.observed_value),
                "Threshold / Rule": a.threshold_or_rule,
                "Message": a.message,
                "Suggested Remediation": a.suggested_action
            })

    if anom_rows:
        st.dataframe(pd.DataFrame(anom_rows), use_container_width=True)
    else:
        st.success("Zero anomalies detected! Telemetry is 100% compliant with operational rules.")

# -----------------
# Tab 4: Export
# -----------------
with tab_export:
    st.subheader("Generate & Download Validation Reports")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button("Generate JSON Audit Report", use_container_width=True):
            json_path = exporter.export_to_json(batch_summary)
            with open(json_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="Download JSON File",
                    data=f.read(),
                    file_name=json_path.name,
                    mime="application/json"
                )
            st.success(f"Generated {json_path.name}")

    with col_e2:
        if st.button("Generate CSV Anomaly Table", use_container_width=True):
            csv_path = exporter.export_anomalies_to_csv(batch_summary)
            with open(csv_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="Download CSV File",
                    data=f.read(),
                    file_name=csv_path.name,
                    mime="text/csv"
                )
            st.success(f"Generated {csv_path.name}")
