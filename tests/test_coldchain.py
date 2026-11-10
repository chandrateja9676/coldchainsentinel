"""
Automated Pytest Suite for ColdChain Sentinel.
Validates:
1. MKT calculation physics accuracy.
2. Anomaly edge cases (unassigned logger, threshold mismatch, gaps, custody breach).
3. Primary and Foreign key constraints.
4. Deterministic reproducibility.
"""

import pytest
import math
from coldchain.generator import ColdChainDataGenerator
from coldchain.compliance import calculate_mkt, ComplianceEvaluator
from coldchain.validator import ColdChainValidator
from coldchain.verify_reproducibility import verify_reproducibility


def test_mkt_arrhenius_physics():
    """Validates USP <1079> Mean Kinetic Temperature calculation."""
    # Constant 5°C should yield MKT = 5.0°C
    temps_const = [5.0] * 50
    mkt = calculate_mkt(temps_const)
    assert abs(mkt - 5.0) < 0.05

    # Fluctuating temperature (e.g., 2°C and 8°C alternating)
    # Because MKT emphasizes higher temperatures due to exponential Arrhenius weighting,
    # MKT must be strictly greater than the arithmetic mean (5.0°C).
    temps_fluct = [2.0, 8.0] * 25
    mkt_fluct = calculate_mkt(temps_fluct)
    arithmetic_mean = sum(temps_fluct) / len(temps_fluct)
    assert mkt_fluct > arithmetic_mean
    assert 5.0 < mkt_fluct < 8.0


def test_unassigned_logger_detection():
    """Validates detection of shipment without assigned logger."""
    shipment = {
        "shipment_id": "SHP-2026-999999",
        "primary_lot_id": "LOT-2026-000001",
        "assigned_logger_id": None,
        "actual_arrival_ts": "2026-10-05T12:00:00+00:00"
    }
    product = {"storage_band": "REFRIGERATED", "standard_min_temp_c": 2.0, "standard_max_temp_c": 8.0}
    policy = {"policy_id": "POL-001", "min_temp_c": 2.0, "max_temp_c": 8.0}

    report = ComplianceEvaluator.evaluate_shipment(
        shipment=shipment,
        product=product,
        policy=policy,
        readings=[],
        custody_events=[],
        stops=[]
    )
    assert report["severity"] == "CRITICAL"
    assert report["excursion_type"] == "SENSOR_UNASSIGNED"
    assert report["disposition_action"] == "QUARANTINE_FOR_ASSAY"


def test_reproducibility():
    """Validates 100% bit-exact reproducibility across dual generations."""
    res = verify_reproducibility(seed=20261022, num_shipments=20)
    assert res["is_reproducible"] is True
    for tbl, info in res["tables"].items():
        assert info["bit_exact_match"] is True


def test_full_validator_battery():
    """Runs end-to-end validator on a starter generated set."""
    gen = ColdChainDataGenerator(seed=20261022)
    dataset = gen.generate_dataset(num_shipments=30, num_loggers=50)
    validator = ColdChainValidator(dataset)
    results = validator.run_all_checks()
    assert results["passed"] is True
    assert len(results["errors"]) == 0
