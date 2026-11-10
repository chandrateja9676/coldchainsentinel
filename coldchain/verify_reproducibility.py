"""
Step 10: Reproducibility Verification Script.
Generates dataset twice with the identical seed and compares SHA-256 digests & row counts.
Demonstrates 100% bit-level reproducibility.
"""

from __future__ import annotations
import json
import hashlib
from typing import Dict, Any
from coldchain.generator import ColdChainDataGenerator


def hash_table(records: list) -> str:
    """Computes deterministic SHA-256 checksum of table records."""
    serialized = json.dumps(records, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_reproducibility(seed: int = 20261022, num_shipments: int = 50) -> Dict[str, Any]:
    """Runs dual generation and verifies bit-for-bit equality."""
    print(f"[*] Running Run 1 with seed={seed}, shipments={num_shipments}...")
    gen1 = ColdChainDataGenerator(seed=seed)
    data1 = gen1.generate_dataset(num_shipments=num_shipments)

    print(f"[*] Running Run 2 with seed={seed}, shipments={num_shipments}...")
    gen2 = ColdChainDataGenerator(seed=seed)
    data2 = gen2.generate_dataset(num_shipments=num_shipments)

    results = {
        "seed": seed,
        "is_reproducible": True,
        "tables": {}
    }

    all_match = True
    for table_name in data1.keys():
        t1 = data1[table_name]
        t2 = data2[table_name]
        count1 = len(t1)
        count2 = len(t2)
        hash1 = hash_table(t1)
        hash2 = hash_table(t2)

        matched = (count1 == count2) and (hash1 == hash2)
        if not matched:
            all_match = False

        results["tables"][table_name] = {
            "row_count": count1,
            "hash_run_1": hash1[:16],
            "hash_run_2": hash2[:16],
            "bit_exact_match": matched
        }

    results["is_reproducible"] = all_match
    return results


if __name__ == "__main__":
    res = verify_reproducibility()
    print("\n================ REPRODUCIBILITY REPORT ================")
    print(f"Deterministic Seed: {res['seed']}")
    print(f"Overall Reproducibility Match: {'PASSED (100% Bit-Exact)' if res['is_reproducible'] else 'FAILED'}")
    print("--------------------------------------------------------")
    for tbl, info in res["tables"].items():
        status = "MATCH" if info["bit_exact_match"] else "MISMATCH"
        print(f"{tbl:<22} | Rows: {info['row_count']:<6} | Hash: {info['hash_run_1']}... | [{status}]")
    print("========================================================\n")
