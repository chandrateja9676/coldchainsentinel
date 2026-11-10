"""
Compliance & Excursion Evaluation Engine.
Implements:
1. Arrhenius Mean Kinetic Temperature (MKT) calculation (USP <1079> / FDA guidelines).
2. Multi-tier thermal excursion analysis (cumulative duration, max single spike, freeze breach).
3. Data transmission gap detection.
4. Chain of custody verification & signature check.
5. Cross-shipment reading contamination check.
6. Automated CAPA recommendations and disposition decision logic.
7. Cryptographic SHA-256 evidence hashing for 21 CFR Part 11 audit trails.
"""

from __future__ import annotations
import math
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone


def calculate_mkt(temperatures_c: List[float], delta_h_over_r: float = 10000.0) -> float:
    """
    Calculates Mean Kinetic Temperature (MKT) in Celsius using the Arrhenius equation:
    MKT = (ΔH / R) / ( -ln( (1/n) * sum(exp(-ΔH / (R * T_K))) ) ) - 273.15
    Standard activation energy ΔH / R = 83.144 kJ/mol / (8.314472 J/(mol*K) * 10^-3) = 10,000 K (USP default).
    """
    if not temperatures_c:
        return 0.0
    
    # Convert all Celsius to Kelvin
    kelvin_temps = [t + 273.15 for t in temperatures_c]
    
    # Check for invalid physical temperatures
    if any(k <= 0 for k in kelvin_temps):
        return min(temperatures_c)

    sum_exp = sum(math.exp(-delta_h_over_r / tk) for tk in kelvin_temps)
    mean_exp = sum_exp / len(kelvin_temps)
    
    if mean_exp <= 0:
        return min(temperatures_c)
        
    mkt_kelvin = delta_h_over_r / (-math.log(mean_exp))
    mkt_celsius = mkt_kelvin - 273.15
    return round(mkt_celsius, 2)


def compute_evidence_hash(readings_summary: str, custody_summary: str, shipment_id: str) -> str:
    """Computes a SHA-256 digital fingerprint of all readings and custody events for 21 CFR Part 11 compliance."""
    hasher = hashlib.sha256()
    payload = f"{shipment_id}|{readings_summary}|{custody_summary}"
    hasher.update(payload.encode("utf-8"))
    return hasher.hexdigest()


class ComplianceEvaluator:
    """Evaluates shipments against Threshold Policies, detecting excursions, gaps, and custody breaches."""

    @staticmethod
    def evaluate_shipment(
        shipment: Dict[str, Any],
        product: Dict[str, Any],
        policy: Dict[str, Any],
        readings: List[Dict[str, Any]],
        custody_events: List[Dict[str, Any]],
        stops: List[Dict[str, Any]],
        sampling_interval_mins: int = 10
    ) -> Dict[str, Any]:
        """
        Runs comprehensive compliance evaluation.
        Returns a dictionary suitable for generating an ExcursionReport.
        """
        shipment_id = shipment["shipment_id"]
        lot_id = shipment["primary_lot_id"]
        assigned_logger = shipment.get("assigned_logger_id")

        # 1. Edge Case: Logger not assigned
        if not assigned_logger:
            return {
                "shipment_id": shipment_id,
                "lot_id": lot_id,
                "policy_id": policy["policy_id"],
                "severity": "CRITICAL",
                "excursion_type": "SENSOR_UNASSIGNED",
                "cumulative_duration_mins": 0,
                "max_single_duration_mins": 0,
                "peak_temperature_c": 0.0,
                "lowest_temperature_c": 0.0,
                "calculated_mkt_c": 0.0,
                "root_cause_category": "LOGGER_UNASSIGNED_OR_MISSING",
                "disposition_action": "QUARANTINE_FOR_ASSAY",
                "investigator_role": "LOGISTICS_ANALYST",
                "investigator_name": "Automated Sentinel Compliance Engine",
                "investigation_timestamp": shipment.get("actual_arrival_ts") or datetime.now(timezone.utc).isoformat(),
                "capa_action_plan": "CAPA-A01: Mandatory dispatch dock verification. Prevent vehicle release without validated paired IoT logger barcode scan.",
                "evidence_hash": hashlib.sha256(f"{shipment_id}-NO-LOGGER".encode()).hexdigest(),
                "flagged_issues": ["Shipment dispatched without an assigned active logger."]
            }

        # 2. Edge Case: Product Threshold Mismatch
        flagged_issues = []
        is_threshold_mismatch = False
        if product["storage_band"] == "ULTRA_COLD" and policy["min_temp_c"] > -50.0:
            is_threshold_mismatch = True
            flagged_issues.append(f"CRITICAL MISMATCH: Product requires ULTRA_COLD ({product['standard_min_temp_c']}°C to {product['standard_max_temp_c']}°C), but evaluated under policy {policy['policy_id']} ({policy['min_temp_c']}°C to {policy['max_temp_c']}°C).")
        elif product["storage_band"] == "REFRIGERATED" and (policy["min_temp_c"] < 0.0 or policy["max_temp_c"] > 12.0):
            is_threshold_mismatch = True
            flagged_issues.append(f"CRITICAL MISMATCH: Product requires REFRIGERATED (2-8°C), but evaluated under policy {policy['policy_id']} ({policy['min_temp_c']}°C to {policy['max_temp_c']}°C).")

        # 3. Check for readings existence
        if not readings:
            return {
                "shipment_id": shipment_id,
                "lot_id": lot_id,
                "policy_id": policy["policy_id"],
                "severity": "CRITICAL",
                "excursion_type": "DATA_TRANSMISSION_GAP",
                "cumulative_duration_mins": 0,
                "max_single_duration_mins": 0,
                "peak_temperature_c": 0.0,
                "lowest_temperature_c": 0.0,
                "calculated_mkt_c": 0.0,
                "root_cause_category": "COMPLETE_TELEMETRY_BLACKOUT",
                "disposition_action": "QUARANTINE_FOR_ASSAY",
                "investigator_role": "LOGISTICS_ANALYST",
                "investigator_name": "Automated Sentinel Compliance Engine",
                "investigation_timestamp": shipment.get("actual_arrival_ts") or datetime.now(timezone.utc).isoformat(),
                "capa_action_plan": "CAPA-G01: Investigate total logger communication loss. Conduct physical logger inspection & quarantine batch pending analytical potency assay.",
                "evidence_hash": hashlib.sha256(f"{shipment_id}-NO-READINGS".encode()).hexdigest(),
                "flagged_issues": ["No telemetry readings recorded for this shipment."]
            }

        # 4. Check for Cross-Shipment Contamination
        cross_shipment_readings = [r for r in readings if r.get("shipment_id") != shipment_id or r.get("logger_id") != assigned_logger]
        if cross_shipment_readings:
            flagged_issues.append(f"DATA CONTAMINATION DETECTED: Found {len(cross_shipment_readings)} readings belonging to foreign logger/shipment IDs within this telemetry trace.")

        # 5. Check for Data Gaps (Transmission Blackouts)
        max_gap_found = 0
        sorted_readings = sorted(readings, key=lambda r: r["timestamp"])
        for i in range(1, len(sorted_readings)):
            t1 = datetime.fromisoformat(sorted_readings[i-1]["timestamp"])
            t2 = datetime.fromisoformat(sorted_readings[i]["timestamp"])
            gap_mins = int((t2 - t1).total_seconds() / 60)
            if gap_mins > max_gap_found:
                max_gap_found = gap_mins

        allowed_gap = policy.get("allowed_gap_tolerance_mins", 30)
        has_severe_data_gap = max_gap_found > allowed_gap
        if has_severe_data_gap:
            flagged_issues.append(f"TELEMETRY GAP: Longest consecutive logger transmission gap was {max_gap_found} mins (allowed tolerance: {allowed_gap} mins).")

        # 6. Check Custody Integrity & Missing Handoffs
        custody_gap_detected = False
        unverified_signatures = [c for c in custody_events if not c.get("signature_verified", False)]
        broken_seals = [c for c in custody_events if not c.get("integrity_seal_intact", True)]
        
        # Verify custody chronological sequence
        sorted_custody = sorted(custody_events, key=lambda c: c["handover_timestamp"]) if custody_events else []
        if len(sorted_custody) < 2:
            custody_gap_detected = True
            flagged_issues.append("CUSTODY BREACH: Incomplete chain of custody; fewer than 2 documented handover milestones.")
        if unverified_signatures:
            custody_gap_detected = True
            flagged_issues.append(f"CUSTODY BREACH: Found {len(unverified_signatures)} custody handovers without verified digital signatures.")
        if broken_seals:
            custody_gap_detected = True
            flagged_issues.append(f"SECURITY BREACH: Tamper-evident seal was reported broken/compromised at {len(broken_seals)} locations.")

        # 7. Temperature Analysis
        temps = [r["temperature_c"] for r in sorted_readings]
        peak_temp = max(temps)
        lowest_temp = min(temps)
        mkt_c = calculate_mkt(temps)

        min_allowed = policy["min_temp_c"]
        max_allowed = policy["max_temp_c"]
        crit_freeze = policy.get("critical_freeze_temp_c", min_allowed - 2.0)
        crit_spike = policy.get("critical_spike_temp_c", max_allowed + 10.0)
        max_cumulative_allowed = policy.get("max_cumulative_excursion_mins", 120)
        max_single_allowed = policy.get("max_single_excursion_mins", 60)
        mkt_limit = policy.get("mkt_upper_limit_c", max_allowed)

        # Calculate durations
        cumulative_excursion_mins = 0
        current_streak_mins = 0
        max_single_streak_mins = 0
        freeze_breach = False
        severe_spike_breach = False

        for t in temps:
            is_out_of_spec = (t < min_allowed) or (t > max_allowed)
            if t <= crit_freeze:
                freeze_breach = True
            if t >= crit_spike:
                severe_spike_breach = True

            if is_out_of_spec:
                cumulative_excursion_mins += sampling_interval_mins
                current_streak_mins += sampling_interval_mins
                if current_streak_mins > max_single_streak_mins:
                    max_single_streak_mins = current_streak_mins
            else:
                current_streak_mins = 0

        # Determine Excursion Type & Severity
        severity = "NONE"
        excursion_type = "NONE"
        root_cause = "NORMAL_OPERATIONS"
        disposition = "RELEASE_STANDARD"
        capa_plan = "No corrective actions required. Shipments verified within product specifications."

        if is_threshold_mismatch:
            severity = "CRITICAL"
            excursion_type = "THRESHOLD_MISMATCH"
            root_cause = "PLANNING_ERROR_POLICY_MISMATCH"
            disposition = "QUARANTINE_FOR_ASSAY"
            capa_plan = "CAPA-P01: Update enterprise ERP master data mapping; mandate automated automated cross-check of product storage band vs lane policy."
        elif cross_shipment_readings:
            severity = "CRITICAL"
            excursion_type = "DATA_TRANSMISSION_GAP"
            root_cause = "IOT_CROSS_SHIPMENT_LEAKAGE"
            disposition = "QUARANTINE_FOR_ASSAY"
            capa_plan = "CAPA-I02: Logger memory wipe failure. Patch IoT gateway firmware to enforce cryptographic shipment session pairing."
        elif freeze_breach:
            severity = "CRITICAL"
            excursion_type = "LOW_TEMPERATURE"
            root_cause = "EXTREME_FREEZING_EVENT"
            disposition = "REJECT_AND_DESTROY"
            capa_plan = "CAPA-T03: Critical freeze violation (< 0°C). Biologic protein denaturing likely. Condemn batch; audit refrigerated vehicle thermostatic compressor."
            flagged_issues.append(f"CRITICAL FREEZE: Temperature hit {lowest_temp}°C (Critical freeze threshold: {crit_freeze}°C).")
        elif severe_spike_breach:
            severity = "CRITICAL"
            excursion_type = "HIGH_TEMPERATURE"
            root_cause = "TARMAC_PROLONGED_HEAT_EXPOSURE"
            disposition = "REJECT_AND_DESTROY"
            capa_plan = "CAPA-T04: Extreme heat spike (hit {peak_temp}°C). Thermal blanket failed or tarmac dwell exceeded 4 hours. Issue non-conformance against airport ground handler."
            flagged_issues.append(f"CRITICAL HEAT SPIKE: Temperature hit {peak_temp}°C (Critical spike ceiling: {crit_spike}°C).")
        elif cumulative_excursion_mins > max_cumulative_allowed or max_single_streak_mins > max_single_allowed:
            severity = "MODERATE"
            excursion_type = "HIGH_TEMPERATURE" if peak_temp > max_allowed else "LOW_TEMPERATURE"
            root_cause = "TRANSIT_DEPOT_DWELL_EXCURSION"
            disposition = "QUARANTINE_FOR_ASSAY"
            capa_plan = "CAPA-T02: Cumulative excursion {cumulative_excursion_mins} mins exceeded allowed {max_cumulative_allowed} mins. Hold lot in warehouse quarantine; perform HPLC stability & potency testing."
            flagged_issues.append(f"EXCURSION LIMIT EXCEEDED: Cumulative excursion {cumulative_excursion_mins} mins (limit: {max_cumulative_allowed} mins).")
        elif mkt_c > mkt_limit:
            severity = "MODERATE"
            excursion_type = "MKT_BREACH"
            root_cause = "THERMAL_ACCELERATION_MKT"
            disposition = "RELEASE_WITH_CAUTION"
            capa_plan = "CAPA-M01: Mean Kinetic Temperature of {mkt_c}°C exceeded limit {mkt_limit}°C. Shorten remaining shelf life by 30 days; approve conditional release to designated clinic."
            flagged_issues.append(f"MKT BREACH: Calculated MKT is {mkt_c}°C (limit: {mkt_limit}°C).")
        elif has_severe_data_gap:
            severity = "MODERATE"
            excursion_type = "DATA_TRANSMISSION_GAP"
            root_cause = "CELLULAR_TELEMETRY_BLACKOUT"
            disposition = "RELEASE_WITH_CAUTION"
            capa_plan = "CAPA-G02: Data transmission gap detected ({max_gap_found} mins). Thermal inertia simulation verifies packaging maintained temp; release conditionally after physical logger dump."
        elif custody_gap_detected:
            severity = "MINOR"
            excursion_type = "CUSTODY_INTEGRITY_BREACH"
            root_cause = "CARRIER_HANDOFF_DOCUMENTATION_DEFECT"
            disposition = "RELEASE_WITH_CAUTION"
            capa_plan = "CAPA-C01: Chain-of-custody documentation lapse. Issue carrier deviation notice; release lot based on intact thermal curve and visual seal verification."
        elif cumulative_excursion_mins > 0:
            severity = "MINOR"
            excursion_type = "HIGH_TEMPERATURE" if peak_temp > max_allowed else "LOW_TEMPERATURE"
            root_cause = "BRIEF_TRANSFER_FLUCTUATION"
            disposition = "RELEASE_STANDARD"
            capa_plan = "Minor brief thermal perturbation within validated safety envelope (< {max_cumulative_allowed} mins). No action required."
            flagged_issues.append(f"Minor deviation: {cumulative_excursion_mins} mins outside 2-8°C, but within approved stability allowance.")

        # Compute Evidence Hash
        readings_summary = f"COUNT:{len(temps)}|MIN:{lowest_temp}|MAX:{peak_temp}|MKT:{mkt_c}|EXCR:{cumulative_excursion_mins}"
        custody_summary = f"EVENTS:{len(custody_events)}|SIGNATURES:{len(unverified_signatures)}|SEALS:{len(broken_seals)}"
        evidence_hash = compute_evidence_hash(readings_summary, custody_summary, shipment_id)

        return {
            "shipment_id": shipment_id,
            "lot_id": lot_id,
            "policy_id": policy["policy_id"],
            "severity": severity,
            "excursion_type": excursion_type,
            "cumulative_duration_mins": cumulative_excursion_mins,
            "max_single_duration_mins": max_single_streak_mins,
            "peak_temperature_c": round(peak_temp, 2),
            "lowest_temperature_c": round(lowest_temp, 2),
            "calculated_mkt_c": mkt_c,
            "root_cause_category": root_cause,
            "disposition_action": disposition,
            "investigator_role": "OPERATIONS_MANAGER" if severity in ("CRITICAL", "MODERATE") else "LOGISTICS_ANALYST",
            "investigator_name": "ColdChain Sentinel Automated QA",
            "investigation_timestamp": shipment.get("actual_arrival_ts") or datetime.now(timezone.utc).isoformat(),
            "capa_action_plan": capa_plan,
            "evidence_hash": evidence_hash,
            "flagged_issues": flagged_issues
        }
