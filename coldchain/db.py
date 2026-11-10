"""
Database Layer & Multi-Format Exporter for Cold Chain Sentinel.
Supports SQLite with foreign keys & indexing, plus CSV and JSON serialization.
"""

from __future__ import annotations
import sqlite3
import json
import csv
import os
from typing import Dict, Any, List


class ColdChainDatabase:
    """Manages SQLite schema, bulk ingestion, and exports."""

    DDL_STATEMENTS = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT NOT NULL,
        therapeutic_class TEXT NOT NULL,
        storage_band TEXT NOT NULL,
        standard_min_temp_c REAL NOT NULL,
        standard_max_temp_c REAL NOT NULL,
        critical_freeze_point_c REAL NOT NULL,
        shelf_life_days INTEGER NOT NULL,
        manufacturer TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS packagings (
        packaging_id TEXT PRIMARY KEY,
        packaging_type TEXT NOT NULL,
        insulation_type TEXT NOT NULL,
        refrigerant_type TEXT NOT NULL,
        rated_protection_hours INTEGER NOT NULL,
        tare_weight_kg REAL NOT NULL,
        max_payload_volume_l REAL NOT NULL,
        validated_ambient_max_c REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS policies (
        policy_id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        route_type TEXT NOT NULL,
        min_temp_c REAL NOT NULL,
        max_temp_c REAL NOT NULL,
        critical_freeze_temp_c REAL NOT NULL,
        critical_spike_temp_c REAL NOT NULL,
        max_cumulative_excursion_mins INTEGER NOT NULL,
        max_single_excursion_mins INTEGER NOT NULL,
        mkt_upper_limit_c REAL NOT NULL,
        allowed_gap_tolerance_mins INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE IF NOT EXISTS lots (
        lot_id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        batch_number TEXT NOT NULL,
        manufacture_date TEXT NOT NULL,
        expiration_date TEXT NOT NULL,
        total_units INTEGER NOT NULL,
        available_units INTEGER NOT NULL,
        supplier_id TEXT NOT NULL,
        initial_qa_status TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE IF NOT EXISTS loggers (
        logger_id TEXT PRIMARY KEY,
        serial_number TEXT NOT NULL,
        model TEXT NOT NULL,
        firmware_version TEXT NOT NULL,
        calibration_date TEXT NOT NULL,
        calibration_expiry_date TEXT NOT NULL,
        calibration_uncertainty_c REAL NOT NULL,
        sampling_interval_mins INTEGER NOT NULL,
        battery_level_pct REAL NOT NULL,
        logger_status TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id TEXT PRIMARY KEY,
        primary_lot_id TEXT NOT NULL,
        packaging_id TEXT NOT NULL,
        assigned_logger_id TEXT,
        carrier_name TEXT NOT NULL,
        origin_facility TEXT NOT NULL,
        destination_facility TEXT NOT NULL,
        planned_departure_ts TEXT NOT NULL,
        planned_arrival_ts TEXT NOT NULL,
        actual_departure_ts TEXT,
        actual_arrival_ts TEXT,
        current_status TEXT NOT NULL,
        total_quantity_vials INTEGER NOT NULL,
        declared_value_usd REAL NOT NULL,
        FOREIGN KEY (primary_lot_id) REFERENCES lots(lot_id),
        FOREIGN KEY (packaging_id) REFERENCES packagings(packaging_id)
    );

    CREATE TABLE IF NOT EXISTS shipment_lots (
        bridge_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        lot_id TEXT NOT NULL,
        allocated_quantity INTEGER NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
    );

    CREATE TABLE IF NOT EXISTS route_stops (
        stop_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        sequence_num INTEGER NOT NULL,
        facility_code TEXT NOT NULL,
        facility_name TEXT NOT NULL,
        facility_type TEXT NOT NULL,
        planned_arrival_ts TEXT NOT NULL,
        actual_arrival_ts TEXT NOT NULL,
        planned_departure_ts TEXT NOT NULL,
        actual_departure_ts TEXT NOT NULL,
        dwell_duration_mins INTEGER NOT NULL,
        ambient_temp_estimate_c REAL NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    );

    CREATE TABLE IF NOT EXISTS custody_events (
        custody_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        stop_id TEXT,
        event_type TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        actor_name TEXT NOT NULL,
        location_code TEXT NOT NULL,
        handover_timestamp TEXT NOT NULL,
        digital_signature_hash TEXT NOT NULL,
        signature_verified BOOLEAN NOT NULL,
        integrity_seal_intact BOOLEAN NOT NULL,
        notes TEXT,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    );

    CREATE TABLE IF NOT EXISTS temperature_readings (
        reading_id TEXT PRIMARY KEY,
        logger_id TEXT NOT NULL,
        shipment_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        raw_temperature_c REAL NOT NULL,
        calibration_offset_c REAL NOT NULL,
        sensor_health_flag TEXT NOT NULL,
        battery_voltage_v REAL NOT NULL,
        is_anomaly BOOLEAN NOT NULL
    );

    CREATE TABLE IF NOT EXISTS excursion_reports (
        report_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        lot_id TEXT NOT NULL,
        policy_id TEXT NOT NULL,
        severity TEXT NOT NULL,
        excursion_type TEXT NOT NULL,
        cumulative_duration_mins INTEGER NOT NULL,
        max_single_duration_mins INTEGER NOT NULL,
        peak_temperature_c REAL NOT NULL,
        lowest_temperature_c REAL NOT NULL,
        calculated_mkt_c REAL NOT NULL,
        root_cause_category TEXT NOT NULL,
        disposition_action TEXT NOT NULL,
        investigator_role TEXT NOT NULL,
        investigator_name TEXT NOT NULL,
        investigation_timestamp TEXT NOT NULL,
        capa_action_plan TEXT NOT NULL,
        evidence_hash TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (lot_id) REFERENCES lots(lot_id),
        FOREIGN KEY (policy_id) REFERENCES policies(policy_id)
    );

    CREATE TABLE IF NOT EXISTS ground_truth (
        anomaly_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        anomaly_category TEXT NOT NULL,
        injection_details TEXT NOT NULL,
        expected_severity TEXT NOT NULL,
        expected_disposition TEXT NOT NULL,
        injected_at_stage TEXT NOT NULL
    );

    -- Performance Indexes
    CREATE INDEX IF NOT EXISTS idx_temp_shipment ON temperature_readings(shipment_id);
    CREATE INDEX IF NOT EXISTS idx_temp_logger ON temperature_readings(logger_id);
    CREATE INDEX IF NOT EXISTS idx_temp_timestamp ON temperature_readings(timestamp);
    CREATE INDEX IF NOT EXISTS idx_custody_shipment ON custody_events(shipment_id);
    CREATE INDEX IF NOT EXISTS idx_stops_shipment ON route_stops(shipment_id);
    CREATE INDEX IF NOT EXISTS idx_excursion_shipment ON excursion_reports(shipment_id);
    """

    def __init__(self, db_path: str = "coldchain.db"):
        self.db_path = db_path

    def init_database(self):
        """Initializes tables and indexes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.DDL_STATEMENTS)
            conn.commit()

    def insert_dataset(self, dataset: Dict[str, List[Dict[str, Any]]]):
        """Bulk inserts all generated dataset tables."""
        self.init_database()
        
        table_mapping = {
            "products": "products",
            "packagings": "packagings",
            "policies": "policies",
            "lots": "lots",
            "loggers": "loggers",
            "shipments": "shipments",
            "shipment_lots": "shipment_lots",
            "route_stops": "route_stops",
            "custody_events": "custody_events",
            "temperature_readings": "temperature_readings",
            "excursion_reports": "excursion_reports",
            "ground_truth": "ground_truth"
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for key, table_name in table_mapping.items():
                records = dataset.get(key, [])
                if not records:
                    continue
                columns = list(records[0].keys())
                placeholders = ", ".join(["?"] * len(columns))
                sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                rows = [[rec[c] for c in columns] for rec in records]
                cursor.executemany(sql, rows)
            conn.commit()

    def export_csv(self, dataset: Dict[str, List[Dict[str, Any]]], output_dir: str = "exports/csv"):
        """Exports all dataset entities to standard CSV files."""
        os.makedirs(output_dir, exist_ok=True)
        for name, records in dataset.items():
            if not records:
                continue
            csv_path = os.path.join(output_dir, f"{name}.csv")
            headers = list(records[0].keys())
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(records)

    def export_json(self, dataset: Dict[str, List[Dict[str, Any]]], output_dir: str = "exports/json"):
        """Exports all dataset entities to JSON files."""
        os.makedirs(output_dir, exist_ok=True)
        for name, records in dataset.items():
            json_path = os.path.join(output_dir, f"{name}.json")
            with open(json_path, mode="w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)

    def get_shipment_summary(self, shipment_id: str) -> Dict[str, Any]:
        """Fetches full deep records for a single shipment."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,))
            shp_row = cursor.fetchone()
            if not shp_row:
                return {}
            shp = dict(shp_row)

            cursor.execute("SELECT * FROM lots WHERE lot_id = ?", (shp["primary_lot_id"],))
            lot = dict(cursor.fetchone() or {})

            cursor.execute("SELECT * FROM products WHERE product_id = ?", (lot.get("product_id"),))
            prod = dict(cursor.fetchone() or {})

            cursor.execute("SELECT * FROM policies WHERE product_id = ?", (prod.get("product_id"),))
            policy = dict(cursor.fetchone() or {})

            cursor.execute("SELECT * FROM route_stops WHERE shipment_id = ? ORDER BY sequence_num ASC", (shipment_id,))
            stops = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM custody_events WHERE shipment_id = ? ORDER BY handover_timestamp ASC", (shipment_id,))
            custody = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM temperature_readings WHERE shipment_id = ? ORDER BY timestamp ASC", (shipment_id,))
            readings = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM excursion_reports WHERE shipment_id = ?", (shipment_id,))
            excr = dict(cursor.fetchone() or {})

            cursor.execute("SELECT * FROM ground_truth WHERE shipment_id = ?", (shipment_id,))
            gt = dict(cursor.fetchone() or {})

            return {
                "shipment": shp,
                "lot": lot,
                "product": prod,
                "policy": policy,
                "stops": stops,
                "custody": custody,
                "readings": readings,
                "excursion_report": excr,
                "ground_truth": gt
            }
