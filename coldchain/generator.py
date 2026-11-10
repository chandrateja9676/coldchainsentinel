"""
Deterministic, High-Fidelity Cold Chain Synthetic Data Generator.
Produces master, transactional, time-series, and compliance data across all 10 entities.
Injects controlled ground-truth edge cases and computes derived metrics deterministically.
"""

from __future__ import annotations
import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Generator

from coldchain.models import (
    Product, Lot, Packaging, Logger, Shipment, ShipmentLot,
    RouteStop, CustodyEvent, TemperatureReading, ThresholdPolicy,
    ExcursionReport, GroundTruthAnomaly,
    StorageBand, ProductTherapeuticClass, ShipmentStatus,
    LoggerStatus, CustodyEventType, ActorRole, ExcursionSeverity,
    ExcursionType, DispositionAction, GroundTruthAnomalyType
)
from coldchain.compliance import ComplianceEvaluator, calculate_mkt, compute_evidence_hash


class ColdChainDataGenerator:
    """Deterministic synthetic data generator parameterized by seed and scale."""

    def __init__(self, seed: int = 20261022):
        self.seed = seed
        self.rng = random.Random(seed)
        self.base_start_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)

    def generate_products(self) -> List[Dict[str, Any]]:
        """Generates pharmaceutical product catalog with distinct thermal stability bands."""
        catalog = [
            Product(
                product_id="PRD-001",
                product_name="Comirna-mRNA Ultra",
                therapeutic_class=ProductTherapeuticClass.MRNA_VACCINE.value,
                storage_band=StorageBand.ULTRA_COLD.value,
                standard_min_temp_c=-80.0,
                standard_max_temp_c=-60.0,
                critical_freeze_point_c=-95.0,
                shelf_life_days=270,
                manufacturer="BioNTech-Pfizer Alliance"
            ),
            Product(
                product_id="PRD-002",
                product_name="OncoMab-Hercept 150mg",
                therapeutic_class=ProductTherapeuticClass.MONOCLONAL_ANTIBODY.value,
                storage_band=StorageBand.REFRIGERATED.value,
                standard_min_temp_c=2.0,
                standard_max_temp_c=8.0,
                critical_freeze_point_c=0.0,
                shelf_life_days=730,
                manufacturer="Roche Diagnostics"
            ),
            Product(
                product_id="PRD-003",
                product_name="NovoRapid FlexPen Insulin",
                therapeutic_class=ProductTherapeuticClass.INSULIN_ANALOG.value,
                storage_band=StorageBand.REFRIGERATED.value,
                standard_min_temp_c=2.0,
                standard_max_temp_c=8.0,
                critical_freeze_point_c=0.0,
                shelf_life_days=540,
                manufacturer="Novo Nordisk A/S"
            ),
            Product(
                product_id="PRD-004",
                product_name="Kymriah Autologous CAR-T",
                therapeutic_class=ProductTherapeuticClass.CELL_THERAPY.value,
                storage_band=StorageBand.ULTRA_COLD.value,
                standard_min_temp_c=-85.0,
                standard_max_temp_c=-70.0,
                critical_freeze_point_c=-120.0,
                shelf_life_days=180,
                manufacturer="Novartis Pharma AG"
            ),
            Product(
                product_id="PRD-005",
                product_name="Octapharma Fresh Frozen Plasma",
                therapeutic_class=ProductTherapeuticClass.BLOOD_PLASMA.value,
                storage_band=StorageBand.FROZEN.value,
                standard_min_temp_c=-25.0,
                standard_max_temp_c=-18.0,
                critical_freeze_point_c=-35.0,
                shelf_life_days=365,
                manufacturer="Octapharma AG"
            ),
            Product(
                product_id="PRD-006",
                product_name="Humira Adalimumab 40mg",
                therapeutic_class=ProductTherapeuticClass.MONOCLONAL_ANTIBODY.value,
                storage_band=StorageBand.REFRIGERATED.value,
                standard_min_temp_c=2.0,
                standard_max_temp_c=8.0,
                critical_freeze_point_c=0.0,
                shelf_life_days=730,
                manufacturer="AbbVie Inc."
            ),
        ]
        return [p.__dict__ for p in catalog]

    def generate_packaging(self) -> List[Dict[str, Any]]:
        """Generates thermal shipper configurations."""
        packagings = [
            Packaging(
                packaging_id="PKG-001",
                packaging_type="VIP_PCM_CHILLED",
                insulation_type="Vacuum Insulated Panels (VIP)",
                refrigerant_type="Phase Change Material (+5°C organic paraffin)",
                rated_protection_hours=96,
                tare_weight_kg=14.5,
                max_payload_volume_l=25.0,
                validated_ambient_max_c=35.0
            ),
            Packaging(
                packaging_id="PKG-002",
                packaging_type="DRY_ICE_DEEP_FROZEN",
                insulation_type="VIP with Polyurethane Shell",
                refrigerant_type="Dry Ice Pellets (Solid CO2 -78.5°C)",
                rated_protection_hours=120,
                tare_weight_kg=22.0,
                max_payload_volume_l=18.0,
                validated_ambient_max_c=40.0
            ),
            Packaging(
                packaging_id="PKG-003",
                packaging_type="ACTIVE_RKN_E2",
                insulation_type="Active Compressor & Heating System",
                refrigerant_type="Active R134a Compressor + Heat Exchanger",
                rated_protection_hours=144,
                tare_weight_kg=650.0,
                max_payload_volume_l=1500.0,
                validated_ambient_max_c=45.0
            ),
            Packaging(
                packaging_id="PKG-004",
                packaging_type="EPS_GEL_PACK_STANDARD",
                insulation_type="Expanded Polystyrene Foam (EPS)",
                refrigerant_type="Water-based Ice Gel Packs (0°C)",
                rated_protection_hours=48,
                tare_weight_kg=8.5,
                max_payload_volume_l=15.0,
                validated_ambient_max_c=30.0
            ),
        ]
        return [p.__dict__ for p in packagings]

    def generate_policies(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates cold-chain governance policies matching product bands."""
        policies = []
        for i, prod in enumerate(products):
            pid = prod["product_id"]
            band = prod["storage_band"]
            
            if band == StorageBand.ULTRA_COLD.value:
                p = ThresholdPolicy(
                    policy_id=f"POL-{i+1:03d}",
                    product_id=pid,
                    route_type="GLOBAL_AIR_EXPEDITE",
                    min_temp_c=-80.0,
                    max_temp_c=-60.0,
                    critical_freeze_temp_c=-95.0,
                    critical_spike_temp_c=-45.0,
                    max_cumulative_excursion_mins=60,
                    max_single_excursion_mins=30,
                    mkt_upper_limit_c=-62.0,
                    allowed_gap_tolerance_mins=30
                )
            elif band == StorageBand.FROZEN.value:
                p = ThresholdPolicy(
                    policy_id=f"POL-{i+1:03d}",
                    product_id=pid,
                    route_type="CROSS_BORDER_REEFER",
                    min_temp_c=-25.0,
                    max_temp_c=-15.0,
                    critical_freeze_temp_c=-35.0,
                    critical_spike_temp_c=-10.0,
                    max_cumulative_excursion_mins=120,
                    max_single_excursion_mins=45,
                    mkt_upper_limit_c=-16.0,
                    allowed_gap_tolerance_mins=30
                )
            else: # REFRIGERATED 2-8°C
                p = ThresholdPolicy(
                    policy_id=f"POL-{i+1:03d}",
                    product_id=pid,
                    route_type="PHARMA_COLD_EXPRESS",
                    min_temp_c=2.0,
                    max_temp_c=8.0,
                    critical_freeze_temp_c=0.0,
                    critical_spike_temp_c=15.0,
                    max_cumulative_excursion_mins=120,
                    max_single_excursion_mins=60,
                    mkt_upper_limit_c=8.0,
                    allowed_gap_tolerance_mins=30
                )
            policies.append(p.__dict__)
        return policies

    def generate_lots(self, products: List[Dict[str, Any]], num_lots: int = 100) -> List[Dict[str, Any]]:
        """Generates pharmaceutical production lots."""
        lots = []
        for idx in range(1, num_lots + 1):
            prod = self.rng.choice(products)
            mfg_date = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=self.rng.randint(0, 200))
            exp_date = mfg_date + timedelta(days=prod["shelf_life_days"])
            total_units = self.rng.choice([5000, 10000, 20000, 50000])
            lot = Lot(
                lot_id=f"LOT-2026-{idx:06d}",
                product_id=prod["product_id"],
                batch_number=f"BATCH-2026-X{self.rng.randint(100, 999)}",
                manufacture_date=mfg_date.strftime("%Y-%m-%d"),
                expiration_date=exp_date.strftime("%Y-%m-%d"),
                total_units=total_units,
                available_units=int(total_units * 0.9),
                supplier_id=f"SUP-{self.rng.randint(1, 10):03d}",
                initial_qa_status="APPROVED"
            )
            lots.append(lot.__dict__)
        return lots

    def generate_loggers(self, num_loggers: int = 1000) -> List[Dict[str, Any]]:
        """Generates calibrated IoT temperature loggers."""
        models = [
            ("Sensitech TempTale Ultra BLE", "v3.1.2"),
            ("Elpro LIBERO Gx Real-Time 5G", "v4.0.8"),
            ("Controlant Saga IoT LTE-M", "v2.9.1"),
            ("Tive Solo 5G Multi-Sensor", "v5.2.0")
        ]
        loggers = []
        for idx in range(1, num_loggers + 1):
            model_info = self.rng.choice(models)
            cal_date = datetime(2026, 3, 1, tzinfo=timezone.utc) + timedelta(days=self.rng.randint(0, 120))
            cal_exp = cal_date + timedelta(days=365)
            
            logger = Logger(
                logger_id=f"LOG-{idx:06d}",
                serial_number=f"SN-IOT-{self.rng.randint(100000, 999999)}",
                model=model_info[0],
                firmware_version=model_info[1],
                calibration_date=cal_date.strftime("%Y-%m-%d"),
                calibration_expiry_date=cal_exp.strftime("%Y-%m-%d"),
                calibration_uncertainty_c=round(self.rng.uniform(0.12, 0.20), 2),
                sampling_interval_mins=10,
                battery_level_pct=round(self.rng.uniform(88.0, 100.0), 1),
                logger_status=LoggerStatus.ACTIVE.value
            )
            loggers.append(logger.__dict__)
        return loggers

    def generate_dataset(
        self,
        num_shipments: int = 50,
        num_loggers: int = 100,
        anomaly_ratio: float = 0.12
    ) -> Dict[str, Any]:
        """
        Generates full linked dataset with 10 core entities, bridge tables, and ground truth.
        Supports parameterized volume:
        - Starter: 50 shipments (instantaneous, ~2s)
        - Full: 5,000 shipments, 1,000 loggers
        """
        # Master Tables
        products = self.generate_products()
        packagings = self.generate_packaging()
        policies = self.generate_policies(products)
        num_lots = max(10, int(num_shipments * 0.25))
        lots = self.generate_lots(products, num_lots=num_lots)
        loggers = self.generate_loggers(num_loggers=num_loggers)

        carriers = [
            "FedEx Custom Critical Cold Chain",
            "DHL LifeConEx Expedited",
            "World Courier Bio-Pharma Special",
            "Kuehne+Nagel PharmaChain",
            "DB Schenker Life+ Reefer"
        ]

        origins = [
            ("Basel Central Bio Hub (CH-BSL)", "BSL-HUB"),
            ("Dublin Biopharma Campus (IE-DUB)", "DUB-HUB"),
            ("Cambridge Biotech Center (US-BOS)", "BOS-HUB"),
            ("Marburg Vaccine Facility (DE-MRG)", "FRA-HUB")
        ]

        destinations = [
            ("Tokyo Central Pharma Depot (JP-NRT)", "NRT-DEPOT"),
            ("Singapore Changi Coolport (SG-SIN)", "SIN-COOL"),
            ("Chicago Healthcare Logistics (US-ORD)", "ORD-DEPOT"),
            ("Sydney Clinical Supply Hub (AU-SYD)", "SYD-HUB"),
            ("London Heathrow Pharma Terminal (GB-LHR)", "LHR-CARGO")
        ]

        shipments = []
        shipment_lots = []
        route_stops = []
        custody_events = []
        all_readings = []
        ground_truth = []
        excursion_reports = []

        prod_by_id = {p["product_id"]: p for p in products}
        policy_by_prod = {p["product_id"]: p for p in policies}
        lot_by_id = {l["lot_id"]: l for l in lots}

        # Calculate exact number of edge cases to inject
        num_anomalies = max(5, int(num_shipments * anomaly_ratio))
        # Specific target edge cases required by problem specification:
        anomaly_types = [
            GroundTruthAnomalyType.LOGGER_NOT_ASSIGNED,
            GroundTruthAnomalyType.THRESHOLD_MISMATCH,
            GroundTruthAnomalyType.MISSING_DATA_GAP,
            GroundTruthAnomalyType.CUSTODY_GAP,
            GroundTruthAnomalyType.CROSS_SHIPMENT_CONTAMINATION,
        ]

        # Assign which shipments get which anomaly
        anomaly_assignments: Dict[int, GroundTruthAnomalyType] = {}
        for a_idx in range(num_anomalies):
            assigned_type = anomaly_types[a_idx % len(anomaly_types)]
            # Assign anomaly to shipment index (e.g., shipment 1, 3, 5...)
            shp_idx = (a_idx * 2) + 1
            if shp_idx <= num_shipments:
                anomaly_assignments[shp_idx] = assigned_type

        # Generate Shipments and their transactions
        for idx in range(1, num_shipments + 1):
            shipment_id = f"SHP-2026-{idx:06d}"
            assigned_anomaly = anomaly_assignments.get(idx, GroundTruthAnomalyType.NONE)

            # Pick Lot and Product
            lot = self.rng.choice(lots)
            prod = prod_by_id[lot["product_id"]]
            policy = policy_by_prod[prod["product_id"]]

            # Packaging selection based on product storage band
            if prod["storage_band"] == StorageBand.ULTRA_COLD.value:
                pkg = packagings[1] # Dry ice
            elif prod["storage_band"] == StorageBand.FROZEN.value:
                pkg = packagings[2] # Active RKN / frozen
            else:
                pkg = packagings[0] # VIP PCM Chilled 2-8°C

            # Logger ID convention: LOG-<shipment-id>-01 or mapped from loggers pool
            logger_assigned_id = f"LOG-{shipment_id}-01"
            if assigned_anomaly == GroundTruthAnomalyType.LOGGER_NOT_ASSIGNED:
                actual_assigned_logger = None
            else:
                actual_assigned_logger = logger_assigned_id

            # Timing: Staggered departures across October 2026
            trip_duration_hours = self.rng.randint(24, 60) # 24 to 60 hours trip
            dep_offset = timedelta(days=self.rng.randint(0, 20), hours=self.rng.randint(0, 23))
            dep_time = self.base_start_time + dep_offset
            arr_time = dep_time + timedelta(hours=trip_duration_hours)

            carrier = self.rng.choice(carriers)
            origin_name, origin_code = self.rng.choice(origins)
            dest_name, dest_code = self.rng.choice(destinations)

            shipment = Shipment(
                shipment_id=shipment_id,
                primary_lot_id=lot["lot_id"],
                packaging_id=pkg["packaging_id"],
                assigned_logger_id=actual_assigned_logger,
                carrier_name=carrier,
                origin_facility=origin_name,
                destination_facility=dest_name,
                planned_departure_ts=dep_time.isoformat(),
                planned_arrival_ts=arr_time.isoformat(),
                actual_departure_ts=dep_time.isoformat(),
                actual_arrival_ts=arr_time.isoformat(),
                current_status=ShipmentStatus.DELIVERED.value,
                total_quantity_vials=self.rng.randint(500, 3000),
                declared_value_usd=float(self.rng.randint(40000, 350000))
            )
            shipments.append(shipment.__dict__)

            # Bridge record: ShipmentLot
            shplot = ShipmentLot(
                bridge_id=f"SHPLOT-2026-{idx:06d}",
                shipment_id=shipment_id,
                lot_id=lot["lot_id"],
                allocated_quantity=shipment.total_quantity_vials
            )
            shipment_lots.append(shplot.__dict__)

            # Generate Route Stops (Origin -> Airport/Depot -> Transit Hub -> Destination)
            stops_for_shipment = []
            stop1_arr = dep_time
            stop1_dep = dep_time + timedelta(hours=2)
            s1 = RouteStop(
                stop_id=f"STOP-{shipment_id}-01",
                shipment_id=shipment_id,
                sequence_num=1,
                facility_code=origin_code,
                facility_name=origin_name,
                facility_type="ORIGIN_FACILITY",
                planned_arrival_ts=stop1_arr.isoformat(),
                actual_arrival_ts=stop1_arr.isoformat(),
                planned_departure_ts=stop1_dep.isoformat(),
                actual_departure_ts=stop1_dep.isoformat(),
                dwell_duration_mins=120,
                ambient_temp_estimate_c=round(self.rng.uniform(18.0, 23.0), 1)
            )
            stops_for_shipment.append(s1.__dict__)

            stop2_arr = stop1_dep + timedelta(hours=int(trip_duration_hours * 0.4))
            stop2_dep = stop2_arr + timedelta(hours=4) # Dwell at airport transit hub
            s2 = RouteStop(
                stop_id=f"STOP-{shipment_id}-02",
                shipment_id=shipment_id,
                sequence_num=2,
                facility_code="AIRPORT-TRANSIT",
                facility_name="International Air Cargo Coolport",
                facility_type="AIRPORT_HUB",
                planned_arrival_ts=stop2_arr.isoformat(),
                actual_arrival_ts=stop2_arr.isoformat(),
                planned_departure_ts=stop2_dep.isoformat(),
                actual_departure_ts=stop2_dep.isoformat(),
                dwell_duration_mins=240,
                ambient_temp_estimate_c=round(self.rng.uniform(24.0, 32.0), 1) # Hot tarmac dwell
            )
            stops_for_shipment.append(s2.__dict__)

            stop3_arr = arr_time
            stop3_dep = arr_time + timedelta(hours=1)
            s3 = RouteStop(
                stop_id=f"STOP-{shipment_id}-03",
                shipment_id=shipment_id,
                sequence_num=3,
                facility_code=dest_code,
                facility_name=dest_name,
                facility_type="DESTINATION_DEPOT",
                planned_arrival_ts=stop3_arr.isoformat(),
                actual_arrival_ts=stop3_arr.isoformat(),
                planned_departure_ts=stop3_dep.isoformat(),
                actual_departure_ts=stop3_dep.isoformat(),
                dwell_duration_mins=60,
                ambient_temp_estimate_c=round(self.rng.uniform(19.0, 22.0), 1)
            )
            stops_for_shipment.append(s3.__dict__)
            route_stops.extend(stops_for_shipment)

            # Generate Custody Events (Handoffs)
            custody_for_shipment = []
            c1_hash = hashlib.sha256(f"{shipment_id}-SUPPLIER-HANDOFF".encode()).hexdigest()
            c1 = CustodyEvent(
                custody_id=f"CUST-{shipment_id}-01",
                shipment_id=shipment_id,
                stop_id=s1.stop_id,
                event_type=CustodyEventType.PICKUP_ORIGIN.value,
                actor_role=ActorRole.SUPPLIER.value,
                actor_name="Dr. Aris Thorne (Quality Release)",
                location_code=origin_code,
                handover_timestamp=stop1_dep.isoformat(),
                digital_signature_hash=c1_hash,
                signature_verified=True,
                integrity_seal_intact=True,
                notes="Pre-conditioned packaging loaded, sensor initiated."
            )
            custody_for_shipment.append(c1.__dict__)

            # Custody event 2: Carrier / Airport transfer
            is_custody_gap = (assigned_anomaly == GroundTruthAnomalyType.CUSTODY_GAP)
            c2_sig_ok = False if is_custody_gap else True
            c2_seal_ok = False if is_custody_gap else True
            c2_hash = hashlib.sha256(f"{shipment_id}-AIRPORT-CARGO".encode()).hexdigest() if c2_sig_ok else "INVALID_SIG_CHECKSUM_ERROR"
            c2 = CustodyEvent(
                custody_id=f"CUST-{shipment_id}-02",
                shipment_id=shipment_id,
                stop_id=s2.stop_id,
                event_type=CustodyEventType.AIRPORT_TRANSFER_ORIGIN.value,
                actor_role=ActorRole.CARRIER.value,
                actor_name="Cargo Handler Agent #44",
                location_code="AIRPORT-TRANSIT",
                handover_timestamp=stop2_arr.isoformat(),
                digital_signature_hash=c2_hash,
                signature_verified=c2_sig_ok,
                integrity_seal_intact=c2_seal_ok,
                notes="Tarmac transfer documentation unsigned." if is_custody_gap else "Transfer to airline active storage completed."
            )
            custody_for_shipment.append(c2.__dict__)

            # Custody event 3: Final delivery
            c3_hash = hashlib.sha256(f"{shipment_id}-FINAL-DELIVERY".encode()).hexdigest()
            c3 = CustodyEvent(
                custody_id=f"CUST-{shipment_id}-03",
                shipment_id=shipment_id,
                stop_id=s3.stop_id,
                event_type=CustodyEventType.FINAL_DELIVERY.value,
                actor_role=ActorRole.WAREHOUSE_OPERATOR.value,
                actor_name="M. Dubois (Depot Receiver)",
                location_code=dest_code,
                handover_timestamp=stop3_arr.isoformat(),
                digital_signature_hash=c3_hash,
                signature_verified=True,
                integrity_seal_intact=True,
                notes="Package inspected, sensor retrieved and offloaded."
            )
            custody_for_shipment.append(c3.__dict__)
            custody_events.extend(custody_for_shipment)

            # Generate Temperature Readings (Every 10 minutes)
            shipment_readings = []
            if actual_assigned_logger is not None:
                total_reading_steps = int((arr_time - dep_time).total_seconds() / 600) # every 10 min
                base_target_temp = (policy["min_temp_c"] + policy["max_temp_c"]) / 2.0
                curr_temp = base_target_temp

                # Edge case flags:
                is_missing_gap = (assigned_anomaly == GroundTruthAnomalyType.MISSING_DATA_GAP)
                is_contamination = (assigned_anomaly == GroundTruthAnomalyType.CROSS_SHIPMENT_CONTAMINATION)

                # Controlled thermal excursions for certain shipments (normal trips vs excursions)
                # If not an explicit synthetic edge case, introduce normal variance or realistic excursion
                has_controlled_excursion = (idx % 7 == 0)

                for step_i in range(total_reading_steps):
                    reading_ts = dep_time + timedelta(minutes=step_i * 10)
                    ts_iso = reading_ts.isoformat()

                    # Injected Gap: skip 12 readings (120 mins) during airport dwell
                    if is_missing_gap and (total_reading_steps // 3 <= step_i <= total_reading_steps // 3 + 12):
                        continue

                    # Physics-based thermal simulation:
                    # Random walk with mean reversion toward safe target temp
                    drift = (base_target_temp - curr_temp) * 0.1
                    noise = self.rng.gauss(0, 0.12)
                    curr_temp += drift + noise

                    # If this shipment has a controlled excursion (e.g. airport tarmac heat spike)
                    if has_controlled_excursion and (total_reading_steps // 2 <= step_i <= total_reading_steps // 2 + 15):
                        # Temperature climbs above threshold
                        curr_temp += self.rng.uniform(0.4, 0.8)

                    # Sensor calibration uncertainty (±0.15°C)
                    cal_uncertainty = self.rng.uniform(-0.15, 0.15)
                    sensed_temp = round(curr_temp + cal_uncertainty, 2)
                    raw_temp = round(curr_temp, 2)

                    logger_id_for_reading = actual_assigned_logger
                    shipment_id_for_reading = shipment_id

                    # Edge Case 5: Cross-shipment contamination injection
                    # 5 readings from an unrelated foreign shipment (e.g., SHP-2026-999999 / LOG-FOREIGN-01)
                    if is_contamination and (step_i in range(10, 15)):
                        logger_id_for_reading = "LOG-SHP-2026-999999-01"
                        shipment_id_for_reading = "SHP-2026-999999"

                    reading_id = f"TEMP-{logger_id_for_reading}-{reading_ts.strftime('%Y%m%d%H%M')}"
                    
                    is_anom = (sensed_temp < policy["min_temp_c"]) or (sensed_temp > policy["max_temp_c"])

                    reading = TemperatureReading(
                        reading_id=reading_id,
                        logger_id=logger_id_for_reading,
                        shipment_id=shipment_id_for_reading,
                        timestamp=ts_iso,
                        temperature_c=sensed_temp,
                        raw_temperature_c=raw_temp,
                        calibration_offset_c=round(cal_uncertainty, 2),
                        sensor_health_flag="OK",
                        battery_voltage_v=round(self.rng.uniform(3.18, 3.32), 2),
                        is_anomaly=is_anom
                    )
                    shipment_readings.append(reading.__dict__)

                all_readings.extend(shipment_readings)

            # Evaluate Policy & Generate Compliance / Excursion Report
            # If THRESHOLD_MISMATCH anomaly, evaluate with a mismatched policy (e.g. evaluate mRNA -80°C with 2-8°C policy)
            eval_policy = policy
            if assigned_anomaly == GroundTruthAnomalyType.THRESHOLD_MISMATCH:
                # pick a policy with a conflicting temperature band
                for alt_pol in policies:
                    if alt_pol["min_temp_c"] != policy["min_temp_c"]:
                        eval_policy = alt_pol
                        break

            report_dict = ComplianceEvaluator.evaluate_shipment(
                shipment=shipment.__dict__,
                product=prod,
                policy=eval_policy,
                readings=shipment_readings,
                custody_events=custody_for_shipment,
                stops=stops_for_shipment,
                sampling_interval_mins=10
            )

            report = ExcursionReport(
                report_id=f"EXCR-2026-{idx:06d}",
                shipment_id=shipment_id,
                lot_id=lot["lot_id"],
                policy_id=eval_policy["policy_id"],
                severity=report_dict["severity"],
                excursion_type=report_dict["excursion_type"],
                cumulative_duration_mins=report_dict["cumulative_duration_mins"],
                max_single_duration_mins=report_dict["max_single_duration_mins"],
                peak_temperature_c=report_dict["peak_temperature_c"],
                lowest_temperature_c=report_dict["lowest_temperature_c"],
                calculated_mkt_c=report_dict["calculated_mkt_c"],
                root_cause_category=report_dict["root_cause_category"],
                disposition_action=report_dict["disposition_action"],
                investigator_role=report_dict["investigator_role"],
                investigator_name=report_dict["investigator_name"],
                investigation_timestamp=report_dict["investigation_timestamp"],
                capa_action_plan=report_dict["capa_action_plan"],
                evidence_hash=report_dict["evidence_hash"]
            )
            excursion_reports.append(report.__dict__)

            # Record in Ground Truth (Step 7 requirement: Separate ground truth)
            expected_sev = report_dict["severity"]
            expected_disp = report_dict["disposition_action"]
            gt_record = GroundTruthAnomaly(
                anomaly_id=f"ANOM-2026-{idx:06d}",
                shipment_id=shipment_id,
                anomaly_category=assigned_anomaly.value,
                injection_details=f"Injected flaw: {assigned_anomaly.value}" if assigned_anomaly != GroundTruthAnomalyType.NONE else "Normal operational trip",
                expected_severity=expected_sev,
                expected_disposition=expected_disp,
                injected_at_stage="GENERATION_PIPELINE"
            )
            ground_truth.append(gt_record.__dict__)

        return {
            "products": products,
            "packagings": packagings,
            "policies": policies,
            "lots": lots,
            "loggers": loggers,
            "shipments": shipments,
            "shipment_lots": shipment_lots,
            "route_stops": route_stops,
            "custody_events": custody_events,
            "temperature_readings": all_readings,
            "excursion_reports": excursion_reports,
            "ground_truth": ground_truth
        }
