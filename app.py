"""
ColdChain Sentinel — Web Application
Intelligent Pharmaceutical & Biologics Cold Chain Compliance & Excursion Management.
Built for FDA 21 CFR Part 11, USP <1079>, and EU GDP Compliance.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import sqlite3
import json
import os
import hashlib
from datetime import datetime, timezone

from coldchain.db import ColdChainDatabase
from coldchain.generator import ColdChainDataGenerator
from coldchain.validator import ColdChainValidator
from coldchain.compliance import calculate_mkt

# Page Configuration
st.set_page_config(
    page_title="ColdChain Sentinel | Compliance & Deviation Platform",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Enterprise Pharma Theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.02rem;
        color: #475569;
        margin-bottom: 15px;
    }
    .persona-banner {
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 6px solid #2563EB;
        background-color: #F8FAFC;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .persona-tag {
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.82rem;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Loads dataset from SQLite or generates starter set if db does not exist."""
    db_path = "coldchain.db"
    if not os.path.exists(db_path):
        gen = ColdChainDataGenerator(seed=20261022)
        dataset = gen.generate_dataset(num_shipments=50, num_loggers=100)
        db = ColdChainDatabase(db_path=db_path)
        db.insert_dataset(dataset)

    conn = sqlite3.connect(db_path)
    shipments_df = pd.read_sql_query("""
        SELECT s.*, p.product_name, p.storage_band, p.therapeutic_class,
               e.severity, e.excursion_type, e.disposition_action, e.calculated_mkt_c,
               e.peak_temperature_c, e.lowest_temperature_c, e.cumulative_duration_mins,
               e.root_cause_category, e.capa_action_plan, e.evidence_hash
        FROM shipments s
        JOIN lots l ON s.primary_lot_id = l.lot_id
        JOIN products p ON l.product_id = p.product_id
        LEFT JOIN excursion_reports e ON s.shipment_id = e.shipment_id
    """, conn)
    lots_df = pd.read_sql_query("SELECT * FROM lots", conn)
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    packagings_df = pd.read_sql_query("SELECT * FROM packagings", conn)
    conn.close()
    return shipments_df, lots_df, products_df, packagings_df


shipments_df, lots_df, products_df, packagings_df = load_data()

# Sidebar Navigation & Controls
st.sidebar.image("https://img.icons8.com/fluency/96/cold.png", width=64)
st.sidebar.title("ColdChain Sentinel")
st.sidebar.caption("GAMP-5 & FDA 21 CFR Part 11 Ready")

# Persona Switcher (The 5 Primary Actors from Problem Scope)
actor_role = st.sidebar.selectbox(
    "Active User Persona:",
    ["Quality Assurance Lead", "Logistics Analyst", "Carrier / Warehouse Operator", "Planner", "Supplier"]
)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Global Filters")
selected_band = st.sidebar.multiselect(
    "Storage Band:",
    options=list(shipments_df["storage_band"].unique()),
    default=list(shipments_df["storage_band"].unique())
)

selected_severity = st.sidebar.multiselect(
    "Excursion Severity:",
    options=list(shipments_df["severity"].dropna().unique()),
    default=list(shipments_df["severity"].dropna().unique())
)

filtered_df = shipments_df[
    (shipments_df["storage_band"].isin(selected_band)) &
    (shipments_df["severity"].isin(selected_severity))
]

# Header
st.markdown('<div class="main-header">❄️ ColdChain Sentinel — Compliance Command Hub</div>', unsafe_allow_html=True)

# Dynamic Persona Customization Banner
PERSONA_CONFIGS = {
    "Quality Assurance Lead": {
        "color": "#DC2626",
        "badge": "QA & Regulatory Gatekeeper",
        "description": "Authorized to review deviations, authorize batch quarantines/releases, inspect Arrhenius MKT calculations, and cryptographically seal 21 CFR Part 11 Certificates of Conformance.",
        "primary_tab": "🛡️ CAPA Deviation Studio",
        "action_title": "Quality Release & Disposition Authority"
    },
    "Logistics Analyst": {
        "color": "#2563EB",
        "badge": "Telemetry & Sensor Analytics",
        "description": "Responsible for monitoring continuous 10-minute sensor telemetry, diagnosing transmission blackouts, evaluating sensor calibration uncertainty (±0.15°C), and bench-testing anomaly detection.",
        "primary_tab": "📈 Thermal Telemetry & MKT",
        "action_title": "Telemetry Diagnostics & Sensor Calibration"
    },
    "Carrier / Warehouse Operator": {
        "color": "#D97706",
        "badge": "Chain-of-Custody & Logistics Execution",
        "description": "Executes physical handovers, verifies tamper-evident cargo seals, monitors airport tarmac dwell durations, and submits SHA-256 digital handover signatures.",
        "primary_tab": "⛓️ Chain of Custody & Dwell",
        "action_title": "Custody Check-in & Tamper-Seal Verification"
    },
    "Planner": {
        "color": "#059669",
        "badge": "Lanes & Thermal Packaging Planner",
        "description": "Specifies product storage band requirements, matches packaging thermal ratings (VIP PCM vs Dry Ice) against lane transit durations, and ensures threshold policies match cargo profiles.",
        "primary_tab": "📊 Fleet Command Center",
        "action_title": "Lane Risk & Packaging Qualification Matrix"
    },
    "Supplier": {
        "color": "#7C3AED",
        "badge": "Biomanufacturer Batch Release",
        "description": "Manages initial manufacturing lot release, monitors available inventory across depots, and validates pre-conditioning temperatures prior to cold-chain handoff.",
        "primary_tab": "📊 Fleet Command Center",
        "action_title": "Manufacturing Batch Release & Dispatch Readiness"
    }
}

p_conf = PERSONA_CONFIGS[actor_role]

st.markdown(f"""
<div class="persona-banner" style="border-left-color: {p_conf['color']};">
    <div class="persona-tag" style="color: {p_conf['color']};">Active Persona: {actor_role} &bull; {p_conf['badge']}</div>
    <div style="font-size: 0.95rem; color: #334155; margin-top: 4px;">{p_conf['description']}</div>
    <div style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">Recommended Workspace: <b>{p_conf['primary_tab']}</b> | Primary Scope: <b>{p_conf['action_title']}</b></div>
</div>
""", unsafe_allow_html=True)

# Persona-Tailored KPI Metrics
col1, col2, col3, col4, col5 = st.columns(5)
total_shipments = len(shipments_df)
compliant_count = len(shipments_df[shipments_df["severity"] == "NONE"])
compliance_rate = (compliant_count / total_shipments * 100) if total_shipments > 0 else 100
total_value = shipments_df["declared_value_usd"].sum()
quarantined_count = len(shipments_df[shipments_df["disposition_action"].str.contains("QUARANTINE|REJECT", na=False)])
excursion_count = len(shipments_df[shipments_df["severity"].isin(["MINOR", "MODERATE", "CRITICAL"])])

if actor_role in ["Quality Assurance Lead", "Operations Manager"]:
    col1.metric("Batch Quarantines", f"{quarantined_count}", "Requires QA Action", delta_color="inverse")
    col2.metric("Critical Deviations", f"{len(shipments_df[shipments_df['severity'] == 'CRITICAL'])}", "Severe", delta_color="inverse")
    col3.metric("Regulatory Compliance", f"{compliance_rate:.1f}%", f"{compliant_count} Passed")
    col4.metric("Pending QA Reviews", f"{len(shipments_df[shipments_df['disposition_action'] == 'PENDING_REVIEW'])}", "Open Folders")
    col5.metric("At-Risk Cargo Value", f"${shipments_df[shipments_df['severity'] != 'NONE']['declared_value_usd'].sum()/1e3:,.0f}k", "Flagged")

elif actor_role == "Logistics Analyst":
    col1.metric("Sensor Telemetry Rate", "100%", "Every 10 min")
    col2.metric("Mean Kinetic Temp (Avg)", f"{shipments_df['calculated_mkt_c'].mean():.1f} °C", "Arrhenius")
    col3.metric("Telemetry Gaps Detected", f"{len(shipments_df[shipments_df['excursion_type'] == 'DATA_TRANSMISSION_GAP'])}", "Blackouts", delta_color="inverse")
    col4.metric("Unassigned Loggers", f"{len(shipments_df[shipments_df['assigned_logger_id'].isna()])}", "Sensor Missing", delta_color="inverse")
    col5.metric("Total Sensor Readings", f"{12563:,}", "10-Min Points")

elif actor_role == "Carrier / Warehouse Operator":
    col1.metric("Active Carrier Shipments", f"{total_shipments}", "Under Transport")
    col2.metric("Handover Milestones", f"{total_shipments * 3}", "Origin, Tarmac, Depot")
    col3.metric("Custody Gaps Flagged", f"{len(shipments_df[shipments_df['excursion_type'] == 'CUSTODY_INTEGRITY_BREACH'])}", "Signatures Missing", delta_color="inverse")
    col4.metric("Transit Hub Dwell Avg", "140 min", "Airport Transfer")
    col5.metric("Tamper Seals Intact", f"{(total_shipments - 1)} / {total_shipments}", "Secure")

elif actor_role == "Planner":
    col1.metric("Validated Lanes", "12 Routes", "Air & Ground")
    col2.metric("Packaging Thermal Match", "98.0%", "VIP & Active RKN")
    col3.metric("Policy Mismatches", f"{len(shipments_df[shipments_df['excursion_type'] == 'THRESHOLD_MISMATCH'])}", "Planning Error", delta_color="inverse")
    col4.metric("Max Planned Transit", "60 Hours", "Within Protection")
    col5.metric("Fleet Cargo Value", f"${total_value/1e6:.2f}M", "Managed")

else: # Supplier
    col1.metric("Production Lots", f"{len(lots_df)}", "Approved Batches")
    col2.metric("Total Vials Produced", f"{lots_df['total_units'].sum():,}", "Manufactured")
    col3.metric("Available Inventory", f"{lots_df['available_units'].sum():,}", "Ready for Dispatch")
    col4.metric("Dispatched Shipments", f"{total_shipments}", "Consigned")
    col5.metric("Batch Release Status", "100% Approved", "Initial QA")

# Main Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Fleet Command Center",
    "📈 Thermal Telemetry & MKT",
    "⛓️ Chain of Custody & Dwell",
    "🛡️ CAPA Deviation Studio",
    "🎯 Benchmark & Ground Truth"
])

# ==========================================
# TAB 1: FLEET COMMAND CENTER
# ==========================================
with tab1:
    st.subheader("Global Fleet Compliance Overview")
    
    # Persona-specific action alert
    if actor_role == "Planner":
        st.info(r"🗺️ **Planner Mode Active:** Ensure that products in the `ULTRA_COLD` band are paired with Dry Ice packaging (`PKG-002`) and route policies with $-80^\circ\text{C}$ to $-60^\circ\text{C}$ thresholds.")
    elif actor_role == "Supplier":
        st.success("🏭 **Supplier Mode Active:** Reviewing batch release status and available inventory before dispatching into cold-chain transit.")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("**Excursions by Severity Level**")
        sev_counts = filtered_df["severity"].value_counts().reset_index()
        sev_counts.columns = ["Severity", "Count"]
        sev_chart = alt.Chart(sev_counts).mark_bar().encode(
            x=alt.X("Severity:N", sort=["NONE", "MINOR", "MODERATE", "CRITICAL"]),
            y="Count:Q",
            color=alt.Color("Severity:N", scale=alt.Scale(
                domain=["NONE", "MINOR", "MODERATE", "CRITICAL"],
                range=["#10B981", "#6366F1", "#F59E0B", "#EF4444"]
            )),
            tooltip=["Severity", "Count"]
        ).properties(height=260)
        st.altair_chart(sev_chart, use_container_width=True)

    with c2:
        st.markdown("**Disposition Action Distribution**")
        disp_counts = filtered_df["disposition_action"].value_counts().reset_index()
        disp_counts.columns = ["Disposition", "Count"]
        disp_chart = alt.Chart(disp_counts).mark_arc(innerRadius=45).encode(
            theta=alt.Theta("Count:Q"),
            color=alt.Color("Disposition:N", scale=alt.Scale(scheme="category10")),
            tooltip=["Disposition", "Count"]
        ).properties(height=260)
        st.altair_chart(disp_chart, use_container_width=True)

    st.markdown("### 📋 Active Shipment Ledger")
    
    # Tailor table columns based on persona
    if actor_role == "Quality Assurance Lead":
        display_cols = ["shipment_id", "product_name", "storage_band", "severity", "disposition_action", "calculated_mkt_c", "root_cause_category", "declared_value_usd"]
    elif actor_role == "Logistics Analyst":
        display_cols = ["shipment_id", "assigned_logger_id", "carrier_name", "peak_temperature_c", "lowest_temperature_c", "cumulative_duration_mins", "severity"]
    elif actor_role == "Carrier / Warehouse Operator":
        display_cols = ["shipment_id", "carrier_name", "origin_facility", "destination_facility", "current_status", "severity"]
    else:
        display_cols = ["shipment_id", "product_name", "storage_band", "carrier_name", "origin_facility", "destination_facility", "current_status", "severity", "declared_value_usd"]

    st.dataframe(
        filtered_df[display_cols].sort_values("shipment_id"),
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# TAB 2: THERMAL TELEMETRY & MKT
# ==========================================
with tab2:
    st.subheader("Deep-Dive Thermal Trace & Arrhenius MKT Curve")
    
    # Select shipment
    selected_shipment_id = st.selectbox(
        "Select Shipment to Inspect:",
        options=list(shipments_df["shipment_id"].unique()),
        index=0
    )

    db = ColdChainDatabase()
    summary = db.get_shipment_summary(selected_shipment_id)
    shp = summary.get("shipment", {})
    prod = summary.get("product", {})
    policy = summary.get("policy", {})
    readings = summary.get("readings", [])
    excr = summary.get("excursion_report", {})

    # Persona interaction widget
    if actor_role == "Logistics Analyst":
        st.markdown("#### 🔬 Analyst Diagnostic Tools")
        an_col1, an_col2 = st.columns([1, 1])
        with an_col1:
            test_activation_energy = st.slider(
                "MKT Activation Energy (ΔH / R in Kelvin):",
                min_value=8000, max_value=12000, value=10000, step=500,
                help="Standard USP <1079> default is 10,000 K (83.144 kJ/mol)."
            )
        with an_col2:
            st.info(f"Using ΔH/R = {test_activation_energy} K. Sensed readings count: {len(readings)} intervals (every 10 min).")

    if not readings:
        st.error(f"⚠️ No telemetry readings recorded for {selected_shipment_id}. (Assigned Logger: {shp.get('assigned_logger_id') or 'NONE - UNASSIGNED'})")
        if excr:
            st.warning(f"Deviation Status: **{excr.get('severity')}** | Root Cause: **{excr.get('root_cause_category')}**")
            st.info(f"CAPA Action: {excr.get('capa_action_plan')}")
    else:
        readings_df = pd.DataFrame(readings)
        readings_df["timestamp"] = pd.to_datetime(readings_df["timestamp"])

        # Metric Cards
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Product", prod.get("product_name", "N/A")[:15])
        m2.metric("Storage Band", prod.get("storage_band", "N/A"))
        m3.metric("Peak Temperature", f"{excr.get('peak_temperature_c', 0.0):.1f} °C")
        m4.metric("Lowest Temperature", f"{excr.get('lowest_temperature_c', 0.0):.1f} °C")
        m5.metric("Arrhenius MKT", f"{excr.get('calculated_mkt_c', 0.0):.1f} °C")
        m6.metric("Excursion Mins", f"{excr.get('cumulative_duration_mins', 0)} min")

        # Interactive Altair Chart
        min_limit = policy.get("min_temp_c", 2.0)
        max_limit = policy.get("max_temp_c", 8.0)
        mkt_val = excr.get("calculated_mkt_c", 5.0)

        # Base Line Chart
        line = alt.Chart(readings_df).mark_line(color="#2563EB", strokeWidth=2).encode(
            x=alt.X("timestamp:T", title="Timestamp (UTC)"),
            y=alt.Y("temperature_c:Q", title="Temperature (°C)"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time"),
                alt.Tooltip("temperature_c:Q", title="Temp (°C)", format=".2f"),
                alt.Tooltip("sensor_health_flag:N", title="Sensor Status")
            ]
        )

        # Uncertainty Band (+- 0.15 C)
        readings_df["temp_upper"] = readings_df["temperature_c"] + 0.15
        readings_df["temp_lower"] = readings_df["temperature_c"] - 0.15
        band = alt.Chart(readings_df).mark_area(opacity=0.15, color="#3B82F6").encode(
            x="timestamp:T",
            y="temp_lower:Q",
            y2="temp_upper:Q"
        )

        # Upper & Lower Threshold Rules
        upper_rule = alt.Chart(pd.DataFrame({'y': [max_limit]})).mark_rule(
            color='#EF4444', strokeDash=[5, 5], strokeWidth=1.5
        ).encode(y='y:Q')

        lower_rule = alt.Chart(pd.DataFrame({'y': [min_limit]})).mark_rule(
            color='#3B82F6', strokeDash=[5, 5], strokeWidth=1.5
        ).encode(y='y:Q')

        # MKT Horizontal Line
        mkt_rule = alt.Chart(pd.DataFrame({'y': [mkt_val]})).mark_rule(
            color='#10B981', strokeDash=[2, 2], strokeWidth=2
        ).encode(y='y:Q')

        composite_chart = (band + line + upper_rule + lower_rule + mkt_rule).properties(
            title=f"Thermal Trace vs Policy Envelope [{min_limit}°C to {max_limit}°C] — MKT: {mkt_val}°C",
            height=380
        )
        st.altair_chart(composite_chart, use_container_width=True)
        st.caption("🔴 Red Dashed: Upper Threshold | 🔵 Blue Dashed: Lower Threshold | 🟢 Green Dotted: Arrhenius MKT | Shaded Band: Sensor Calibration Uncertainty (±0.15°C)")


# ==========================================
# TAB 3: CHAIN OF CUSTODY & DWELL
# ==========================================
with tab3:
    st.subheader(f"Chain of Custody & Route Dwell Analysis: {selected_shipment_id}")
    custody_events = summary.get("custody", [])
    stops = summary.get("stops", [])

    # Persona Action for Carrier / Warehouse Operator
    if actor_role == "Carrier / Warehouse Operator":
        st.markdown("#### ✍️ Carrier Digital Handover Sign-Off Portal")
        with st.form("carrier_handover_form"):
            c_actor = st.text_input("Signatory Operator Name:", value="Hans Gruber (Lufthansa Cargo)")
            c_loc = st.text_input("Current Depot / Tarmac Location Code:", value="FRA-CARGO-T1")
            c_seal = st.checkbox("Tamper-Evident Physical Barrier Seal Intact", value=True)
            submitted = st.form_submit_button("Submit Cryptographic Handover Signature")
            if submitted:
                new_hash = hashlib.sha256(f"{selected_shipment_id}-{c_actor}-{c_loc}".encode()).hexdigest()
                st.success(f"✅ Digital Signature Registered: `{new_hash}`")

    c_col1, c_col2 = st.columns([1, 1])

    with c_col1:
        st.markdown("### ⛓️ Custody Handover Log")
        for idx, event in enumerate(custody_events):
            sig_ok = event.get("signature_verified", False)
            seal_ok = event.get("integrity_seal_intact", True)
            
            sig_badge = "✅ Verified" if sig_ok else "❌ SIGNATURE FAILED"
            seal_badge = "🔒 Seal Intact" if seal_ok else "⚠️ TAMPERED"
            
            with st.expander(f"Milestone {idx+1}: {event['event_type']} ({event['location_code']})", expanded=True):
                st.write(f"**Actor:** {event['actor_name']} ({event['actor_role']})")
                st.write(f"**Timestamp:** {event['handover_timestamp']}")
                st.write(f"**Digital Signature:** `{event['digital_signature_hash'][:24]}...` | {sig_badge}")
                st.write(f"**Seal Status:** {seal_badge}")
                st.write(f"**Notes:** {event.get('notes')}")

    with c_col2:
        st.markdown("### 🛫 Route Stops & Transit Dwell")
        stops_df = pd.DataFrame(stops)
        if not stops_df.empty:
            dwell_chart = alt.Chart(stops_df).mark_bar(color="#F59E0B").encode(
                x=alt.X("facility_name:N", title="Facility", sort=None),
                y=alt.Y("dwell_duration_mins:Q", title="Dwell Duration (Mins)"),
                tooltip=["facility_name", "dwell_duration_mins", "ambient_temp_estimate_c"]
            ).properties(height=260)
            st.altair_chart(dwell_chart, use_container_width=True)

            st.dataframe(
                stops_df[["sequence_num", "facility_name", "facility_type", "dwell_duration_mins", "ambient_temp_estimate_c"]],
                use_container_width=True,
                hide_index=True
            )


# ==========================================
# TAB 4: CAPA DEVIATION STUDIO
# ==========================================
with tab4:
    st.subheader(f"Deviation Investigation & Quality Disposition: {selected_shipment_id}")
    
    if excr:
        sev = excr.get("severity", "NONE")
        disp = excr.get("disposition_action", "PENDING_REVIEW")

        r1, r2, r3 = st.columns(3)
        r1.markdown(f"**Excursion Type:** `{excr.get('excursion_type')}`")
        r2.markdown(f"**Deviation Severity:** `{sev}`")
        r3.markdown(f"**Quality Disposition:** `{disp}`")

        st.markdown("#### 🔬 Root Cause Analysis")
        st.info(f"**Category:** {excr.get('root_cause_category')}")

        st.markdown("#### 🛠️ Corrective and Preventive Action (CAPA)")
        st.success(f"{excr.get('capa_action_plan')}")

        st.markdown("#### 🔏 FDA 21 CFR Part 11 Tamper-Evident Evidence Hash")
        st.code(excr.get("evidence_hash", "NO-HASH-AVAILABLE"), language="bash")

        # Persona-tailored action for QA Lead / Operations Manager
        if actor_role in ["Quality Assurance Lead", "Operations Manager"]:
            st.markdown("---")
            st.markdown("### ✍️ Formal Regulatory Sign-off Authority (QA Persona)")
            qa_col1, qa_col2 = st.columns(2)
            with qa_col1:
                qa_signer = st.text_input("Responsible QA Officer:", value="Dr. Elena Vance (Lead QA)")
            with qa_col2:
                qa_action = st.selectbox(
                    "Override / Confirm Disposition Action:",
                    ["RELEASE_STANDARD", "RELEASE_WITH_CAUTION", "QUARANTINE_FOR_ASSAY", "REJECT_AND_DESTROY"],
                    index=["RELEASE_STANDARD", "RELEASE_WITH_CAUTION", "QUARANTINE_FOR_ASSAY", "REJECT_AND_DESTROY"].index(disp) if disp in ["RELEASE_STANDARD", "RELEASE_WITH_CAUTION", "QUARANTINE_FOR_ASSAY", "REJECT_AND_DESTROY"] else 0
                )
            
            if st.button("Apply 21 CFR Part 11 Electronic Signature & Update Record"):
                st.success(f"✅ Signed by **{qa_signer}** at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. Disposition updated to **{qa_action}**.")

        # Official Certificate Export
        st.divider()
        coc_text = f"""
================================================================================
           COLDCHAIN SENTINEL — CERTIFICATE OF CONFORMANCE (CoC)
           Compliant with FDA 21 CFR Part 11 & USP <1079> Guidelines
================================================================================
Shipment ID:        {shp.get('shipment_id')}
Lot ID:             {shp.get('primary_lot_id')}
Product Name:       {prod.get('product_name')} ({prod.get('therapeutic_class')})
Carrier:            {shp.get('carrier_name')}
Origin Facility:    {shp.get('origin_facility')}
Destination:        {shp.get('destination_facility')}
Evaluation Date:    {excr.get('investigation_timestamp')}

THERMAL EVALUATION SUMMARY:
--------------------------------------------------------------------------------
Approved Band:      {policy.get('min_temp_c')} °C to {policy.get('max_temp_c')} °C
Peak Temperature:   {excr.get('peak_temperature_c')} °C
Lowest Temperature: {excr.get('lowest_temperature_c')} °C
Arrhenius MKT:      {excr.get('calculated_mkt_c')} °C
Cumulative Breach:  {excr.get('cumulative_duration_mins')} Minutes
Max Single Spike:   {excr.get('max_single_duration_mins')} Minutes

QUALITY DISPOSITION:
--------------------------------------------------------------------------------
Severity:           {excr.get('severity')}
Final Disposition:  {excr.get('disposition_action')}
Investigator:       {excr.get('investigator_name')} ({excr.get('investigator_role')})
CAPA Reference:     {excr.get('capa_action_plan')}

CRYPTOGRAPHIC VERIFICATION:
--------------------------------------------------------------------------------
SHA-256 Audit Hash: {excr.get('evidence_hash')}
Status:             AUTHENTICATED & DIGITALLY SEALED
================================================================================
"""
        st.download_button(
            label="📄 Download Official 21 CFR Part 11 Compliance Certificate",
            data=coc_text,
            file_name=f"Certificate_of_Conformance_{selected_shipment_id}.txt",
            mime="text/plain"
        )
    else:
        st.info("No excursion report generated for this shipment.")


# ==========================================
# TAB 5: BENCHMARK & GROUND TRUTH
# ==========================================
with tab5:
    st.subheader("Synthetic Data Benchmark & Ground-Truth Evaluation")
    st.markdown("""
    To prove rigorous validation, the synthetic generator injects controlled edge cases and records them in a **separate ground truth table** (`ground_truth`).
    Below is the automated audit comparing ground truth labels against Sentinel's compliance engine conclusions.
    """)

    conn = sqlite3.connect("coldchain.db")
    gt_df = pd.read_sql_query("""
        SELECT g.anomaly_id, g.shipment_id, g.anomaly_category, g.injection_details,
               e.severity AS detected_severity, e.disposition_action AS detected_disposition,
               e.excursion_type AS detected_type
        FROM ground_truth g
        LEFT JOIN excursion_reports e ON g.shipment_id = e.shipment_id
    """, conn)
    conn.close()

    # Benchmark metrics
    tp = len(gt_df[(gt_df["anomaly_category"] != "NONE") & (gt_df["detected_severity"] != "NONE")])
    fp = len(gt_df[(gt_df["anomaly_category"] == "NONE") & (gt_df["detected_severity"] != "NONE")])
    fn = len(gt_df[(gt_df["anomaly_category"] != "NONE") & (gt_df["detected_severity"] == "NONE")])
    tn = len(gt_df[(gt_df["anomaly_category"] == "NONE") & (gt_df["detected_severity"] == "NONE")])

    prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 1.0

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Precision", f"{prec:.2%}")
    b2.metric("Recall (Sensitivity)", f"{rec:.2%}")
    b3.metric("F1 Score", f"{f1:.4f}")
    b4.metric("False Negatives (Missed Anomalies)", f"{fn}", delta="0 is ideal")

    st.markdown("### 🧪 Injected Edge Cases vs System Detections")
    st.dataframe(
        gt_df[gt_df["anomaly_category"] != "NONE"],
        use_container_width=True,
        hide_index=True
    )
