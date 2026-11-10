"""
Data Models and Enums for Cold Chain Compliance & Excursion Management.
Implements the 10 core entities, bridge tables, and ground truth schema.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class StorageBand(str, Enum):
    ULTRA_COLD = "ULTRA_COLD"       # -80°C to -60°C (mRNA, viral vectors)
    FROZEN = "FROZEN"               # -25°C to -15°C (Enzymes, plasma)
    REFRIGERATED = "REFRIGERATED"   # +2°C to +8°C (Monoclonal antibodies, vaccines, insulin)
    CONTROLLED_ROOM_TEMP = "CRT"   # +15°C to +25°C (Oral solid dosage, biologics)


class ProductTherapeuticClass(str, Enum):
    MRNA_VACCINE = "MRNA_VACCINE"
    MONOCLONAL_ANTIBODY = "MONOCLONAL_ANTIBODY"
    INSULIN_ANALOG = "INSULIN_ANALOG"
    CELL_THERAPY = "CELL_THERAPY"
    BLOOD_PLASMA = "BLOOD_PLASMA"
    SPECIALTY_PHARMA = "SPECIALTY_PHARMA"


class ShipmentStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"


class LoggerStatus(str, Enum):
    CALIBRATED = "CALIBRATED"
    ACTIVE = "ACTIVE"
    IN_USE = "IN_USE"
    EXPIRED = "EXPIRED"
    UNASSIGNED = "UNASSIGNED"
    FAULTY = "FAULTY"


class CustodyEventType(str, Enum):
    PICKUP_ORIGIN = "PICKUP_ORIGIN"
    AIRPORT_TRANSFER_ORIGIN = "AIRPORT_TRANSFER_ORIGIN"
    FLIGHT_DEPARTURE = "FLIGHT_DEPARTURE"
    FLIGHT_ARRIVAL = "FLIGHT_ARRIVAL"
    CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE"
    CROSS_DOCK_DEPOT = "CROSS_DOCK_DEPOT"
    FINAL_DELIVERY = "FINAL_DELIVERY"


class ActorRole(str, Enum):
    SUPPLIER = "SUPPLIER"
    PLANNER = "PLANNER"
    CARRIER = "CARRIER"
    WAREHOUSE_OPERATOR = "WAREHOUSE_OPERATOR"
    LOGISTICS_ANALYST = "LOGISTICS_ANALYST"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE"


class ExcursionSeverity(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"


class ExcursionType(str, Enum):
    NONE = "NONE"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    LOW_TEMPERATURE = "LOW_TEMPERATURE"
    MKT_BREACH = "MKT_BREACH"
    DATA_TRANSMISSION_GAP = "DATA_TRANSMISSION_GAP"
    CUSTODY_INTEGRITY_BREACH = "CUSTODY_INTEGRITY_BREACH"
    SENSOR_UNASSIGNED = "SENSOR_UNASSIGNED"
    THRESHOLD_MISMATCH = "THRESHOLD_MISMATCH"


class DispositionAction(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    RELEASE_STANDARD = "RELEASE_STANDARD"
    RELEASE_WITH_CAUTION = "RELEASE_WITH_CAUTION"
    QUARANTINE_FOR_ASSAY = "QUARANTINE_FOR_ASSAY"
    REJECT_AND_DESTROY = "REJECT_AND_DESTROY"


class GroundTruthAnomalyType(str, Enum):
    NONE = "NONE"
    LOGGER_NOT_ASSIGNED = "LOGGER_NOT_ASSIGNED"
    THRESHOLD_MISMATCH = "THRESHOLD_MISMATCH"
    MISSING_DATA_GAP = "MISSING_DATA_GAP"
    CUSTODY_GAP = "CUSTODY_GAP"
    CROSS_SHIPMENT_CONTAMINATION = "CROSS_SHIPMENT_CONTAMINATION"


# ==========================================
# 10 Core Entities
# ==========================================

@dataclass
class Product:
    product_id: str                      # PRD-001
    product_name: str                    # e.g., BioVax-mRNA Covid Booster
    therapeutic_class: str               # ProductTherapeuticClass
    storage_band: str                    # StorageBand
    standard_min_temp_c: float          # e.g., -80.0 or 2.0
    standard_max_temp_c: float          # e.g., -60.0 or 8.0
    critical_freeze_point_c: float      # e.g., 0.0 for 2-8°C biologics
    shelf_life_days: int                # e.g., 365
    manufacturer: str                   # e.g., GenPharma Labs


@dataclass
class Lot:
    lot_id: str                          # LOT-2026-000001
    product_id: str                      # PRD-001
    batch_number: str                    # BATCH-2026-X77
    manufacture_date: str                # YYYY-MM-DD
    expiration_date: str                 # YYYY-MM-DD
    total_units: int                     # e.g., 10000
    available_units: int                 # e.g., 8500
    supplier_id: str                     # SUP-001
    initial_qa_status: str               # APPROVED, PENDING, REJECTED


@dataclass
class Packaging:
    packaging_id: str                    # PKG-001
    packaging_type: str                  # VIP_PCM_BOX, ACTIVE_RKN_CONTAINER, DRY_ICE_SHIPPER
    insulation_type: str                 # Vacuum Insulated Panel (VIP), Polyurethane
    refrigerant_type: str                # Phase Change Material (+5°C), Dry Ice (-78.5°C)
    rated_protection_hours: int          # e.g., 72, 96, 120
    tare_weight_kg: float                # Packaging tare
    max_payload_volume_l: float          # Volume in Liters
    validated_ambient_max_c: float       # Validated ambient external temp limit (e.g., 35°C)


@dataclass
class Logger:
    logger_id: str                       # LOG-SHP-2026-000001-01 (or LOG-0001)
    serial_number: str                   # SN-IOT-99281
    model: str                           # SenseTemp IoT Pro 5G
    firmware_version: str                # v2.4.1
    calibration_date: str                # YYYY-MM-DD
    calibration_expiry_date: str         # YYYY-MM-DD (must be after trip end)
    calibration_uncertainty_c: float     # ±0.20 °C (NIST traceable)
    sampling_interval_mins: int          # 10 mins
    battery_level_pct: float             # 98.5%
    logger_status: str                   # LoggerStatus


@dataclass
class Shipment:
    shipment_id: str                     # SHP-2026-000001
    primary_lot_id: str                  # LOT-2026-000001
    packaging_id: str                    # PKG-001
    assigned_logger_id: Optional[str]    # LOG-SHP-2026-000001-01 (or None for unassigned edge case)
    carrier_name: str                    # FedEx Custom Critical, DHL LifeConEx, World Courier
    origin_facility: str                 # Basel Central Bio Hub (CH-BSL)
    destination_facility: str            # Boston Life Science Depot (US-BOS)
    planned_departure_ts: str            # ISO 8601
    planned_arrival_ts: str              # ISO 8601
    actual_departure_ts: Optional[str]   # ISO 8601
    actual_arrival_ts: Optional[str]     # ISO 8601
    current_status: str                  # ShipmentStatus
    total_quantity_vials: int            # 2500
    declared_value_usd: float            # 125000.00


@dataclass
class ShipmentLot:
    """Bridge table for Shipment <-> Lot (N:M relationship)."""
    bridge_id: str                       # SHPLOT-2026-000001
    shipment_id: str                     # SHP-2026-000001
    lot_id: str                          # LOT-2026-000001
    allocated_quantity: int              # Quantity from this specific lot


@dataclass
class RouteStop:
    stop_id: str                         # STOP-2026-000001-01
    shipment_id: str                     # SHP-2026-000001
    sequence_num: int                    # 1, 2, 3...
    facility_code: str                   # FRA-HUB, JFK-AIRPORT
    facility_name: str                   # Frankfurt Cool Chain Terminal
    facility_type: str                   # AIRPORT_HUB, CROSS_DOCK, TRANSIT_DEPOT, HOSPITAL
    planned_arrival_ts: str              # ISO 8601
    actual_arrival_ts: str               # ISO 8601
    planned_departure_ts: str            # ISO 8601
    actual_departure_ts: str             # ISO 8601
    dwell_duration_mins: int             # e.g., 180 mins
    ambient_temp_estimate_c: float       # Exterior ambient air temperature


@dataclass
class CustodyEvent:
    custody_id: str                      # CUST-2026-000001-01
    shipment_id: str                     # SHP-2026-000001
    stop_id: Optional[str]               # STOP-2026-000001-01
    event_type: str                      # CustodyEventType
    actor_role: str                      # ActorRole
    actor_name: str                      # "Hans Gruber (Lufthansa Cargo)"
    location_code: str                   # "FRA-CARGO-T1"
    handover_timestamp: str              # ISO 8601
    digital_signature_hash: str          # SHA256 signature string
    signature_verified: bool             # True / False
    integrity_seal_intact: bool          # True / False
    notes: str                           # "Cold room transfer verified"


@dataclass
class TemperatureReading:
    reading_id: str                      # TEMP-<logger-id>-<timestamp>
    logger_id: str                       # LOG-SHP-2026-000001-01
    shipment_id: str                     # SHP-2026-000001
    timestamp: str                       # ISO 8601
    temperature_c: float                 # Sensor reading in Celsius
    raw_temperature_c: float             # Uncalibrated raw sensor ADC reading
    calibration_offset_c: float          # e.g., +0.05 °C
    sensor_health_flag: str              # OK, BATTERY_LOW, TRANSMISSION_DELAY, GAP_INTERPOLATED
    battery_voltage_v: float             # 3.29 V
    is_anomaly: bool                     # Whether reading breaches thresholds


@dataclass
class ThresholdPolicy:
    policy_id: str                       # POL-001
    product_id: str                      # PRD-001
    route_type: str                      # INTERNATIONAL_AIR, DOMESTIC_GROUND, REFRIGERATED_TRUCK
    min_temp_c: float                    # e.g., 2.0 °C
    max_temp_c: float                    # e.g., 8.0 °C
    critical_freeze_temp_c: float        # e.g., 0.0 °C
    critical_spike_temp_c: float         # e.g., 15.0 °C
    max_cumulative_excursion_mins: int   # e.g., 120 mins allowed outside 2-8°C
    max_single_excursion_mins: int       # e.g., 60 mins single spike allowed
    mkt_upper_limit_c: float             # e.g., 8.0 °C Mean Kinetic Temperature ceiling
    allowed_gap_tolerance_mins: int      # 30 mins max missing data


@dataclass
class ExcursionReport:
    report_id: str                       # EXCR-2026-000001
    shipment_id: str                     # SHP-2026-000001
    lot_id: str                          # LOT-2026-000001
    policy_id: str                       # POL-001
    severity: str                        # ExcursionSeverity
    excursion_type: str                  # ExcursionType
    cumulative_duration_mins: int        # Cumulative mins outside threshold
    max_single_duration_mins: int        # Longest continuous spike
    peak_temperature_c: float            # Maximum temp reached during shipment
    lowest_temperature_c: float          # Minimum temp reached during shipment
    calculated_mkt_c: float              # Arrhenius Mean Kinetic Temperature
    root_cause_category: str             # TARMAC_PROLONGED_DWELL, REFRIGERATION_FAILURE, etc.
    disposition_action: str              # DispositionAction
    investigator_role: str               # ActorRole
    investigator_name: str               # "Dr. Elena Vance (QA Lead)"
    investigation_timestamp: str         # ISO 8601
    capa_action_plan: str                # Corrective & Preventive Action plan text
    evidence_hash: str                   # SHA256 hash of all readings and custody events


@dataclass
class GroundTruthAnomaly:
    """Separate ground-truth label table for benchmark evaluation; never leaked into model features."""
    anomaly_id: str                      # ANOM-2026-000001
    shipment_id: str                     # SHP-2026-000001
    anomaly_category: str                # GroundTruthAnomalyType
    injection_details: str               # Description of injected flaw
    expected_severity: str               # Expected ExcursionSeverity
    expected_disposition: str            # Expected DispositionAction
    injected_at_stage: str               # Stage where anomaly was introduced
