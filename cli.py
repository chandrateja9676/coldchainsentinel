"""
Unified CLI for ColdChain Sentinel.
Commands:
  python cli.py generate [--seed 20261022] [--scale starter|full] [--export csv,json,sql]
  python cli.py validate
  python cli.py verify
  python cli.py summary
"""

from __future__ import annotations
import argparse
import sys
import os
import json
from datetime import datetime

from coldchain.generator import ColdChainDataGenerator
from coldchain.validator import ColdChainValidator
from coldchain.db import ColdChainDatabase
from coldchain.verify_reproducibility import verify_reproducibility


def cmd_generate(args):
    scale = args.scale.lower()
    seed = args.seed
    export_formats = [f.strip().lower() for f in args.export.split(",")]

    if scale == "full":
        num_shipments = 5000
        num_loggers = 1000
    else:
        num_shipments = 50
        num_loggers = 100

    print(f"\n================ COLDCHAIN SENTINEL DATA GENERATION ================")
    print(f"Scale:               {scale.upper()} ({num_shipments} shipments, {num_loggers} loggers)")
    print(f"Random Seed:         {seed}")
    print(f"Sampling Frequency:  10 minutes")
    print(f"Target Formats:      {', '.join(export_formats).upper()}")
    print("--------------------------------------------------------------------")

    generator = ColdChainDataGenerator(seed=seed)
    print(f"[*] Generating master, transactional, and sensor readings...")
    dataset = generator.generate_dataset(num_shipments=num_shipments, num_loggers=num_loggers)

    print(f"[+] Generated:")
    for k, v in dataset.items():
        print(f"    - {k:<22}: {len(v):>8} records")

    db = ColdChainDatabase(db_path=args.db)

    if "sql" in export_formats or "sqlite" in export_formats:
        print(f"[*] Ingesting into SQLite database ({args.db})...")
        db.insert_dataset(dataset)
        print(f"[+] SQLite database updated: {args.db}")

    if "csv" in export_formats:
        csv_dir = os.path.join(args.output_dir, "csv")
        print(f"[*] Exporting to CSV in {csv_dir}...")
        db.export_csv(dataset, output_dir=csv_dir)
        print(f"[+] CSV export complete ({len(dataset)} files)")

    if "json" in export_formats:
        json_dir = os.path.join(args.output_dir, "json")
        print(f"[*] Exporting to JSON in {json_dir}...")
        db.export_json(dataset, output_dir=json_dir)
        print(f"[+] JSON export complete ({len(dataset)} files)")

    # Run auto-validation
    print(f"\n[*] Running automated validation checks...")
    validator = ColdChainValidator(dataset)
    report = validator.run_all_checks()

    print("\n---------------- VALIDATION SUMMARY ----------------")
    print(f"Overall Result: {'PASSED' if report['passed'] else 'FAILED'}")
    for check_name, status in report["checks"].items():
        print(f"  {check_name:<30}: {status}")

    print("\n---------------- BENCHMARK METRICS -----------------")
    metrics = report["metrics"]
    print(f"  Total Shipments Evaluated: {metrics.get('total_evaluated_shipments')}")
    print(f"  True Positives:            {metrics.get('true_positives')}")
    print(f"  False Positives:           {metrics.get('false_positives')}")
    print(f"  False Negatives:           {metrics.get('false_negatives')}")
    print(f"  Precision:                 {metrics.get('precision'):.4f}")
    print(f"  Recall:                    {metrics.get('recall'):.4f}")
    print(f"  F1 Score:                  {metrics.get('f1_score'):.4f}")
    print("====================================================================\n")


def cmd_validate(args):
    print("\n[*] Loading dataset for validation...")
    generator = ColdChainDataGenerator(seed=args.seed)
    num_shipments = 5000 if args.scale == "full" else 50
    num_loggers = 1000 if args.scale == "full" else 100
    dataset = generator.generate_dataset(num_shipments=num_shipments, num_loggers=num_loggers)

    validator = ColdChainValidator(dataset)
    report = validator.run_all_checks()

    print("\n================ VALIDATION AUDIT REPORT ================")
    print(f"Status: {'PASSED (Zero Defects)' if report['passed'] else 'FAILED'}")
    print("---------------------------------------------------------")
    for check_name, status in report["checks"].items():
        print(f"{check_name:<32}: {status}")
    if report["errors"]:
        print("\nERRORS ENCOUNTERED:")
        for err in report["errors"][:10]:
            print(f"  - {err}")
    print("=========================================================\n")


def cmd_verify(args):
    res = verify_reproducibility(seed=args.seed, num_shipments=50)
    print("\n================ REPRODUCIBILITY VERIFICATION ================")
    print(f"Fixed Seed: {res['seed']}")
    print(f"Reproducibility Status: {'PASSED (100% Bit-Exact Match)' if res['is_reproducible'] else 'FAILED'}")
    print("--------------------------------------------------------------")
    for tbl, info in res["tables"].items():
        match_str = "MATCH" if info["bit_exact_match"] else "MISMATCH"
        print(f"{tbl:<22} | Rows: {info['row_count']:<6} | Hash: {info['hash_run_1']}... | [{match_str}]")
    print("==============================================================\n")


def main():
    parser = argparse.ArgumentParser(description="ColdChain Sentinel CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Generate
    gen_p = subparsers.add_parser("generate", help="Generate synthetic cold chain dataset")
    gen_p.add_argument("--seed", type=int, default=20261022, help="Deterministic random seed")
    gen_p.add_argument("--scale", type=str, default="starter", choices=["starter", "full"], help="Dataset scale")
    gen_p.add_argument("--export", type=str, default="csv,json,sql", help="Comma-separated formats (csv,json,sql)")
    gen_p.add_argument("--db", type=str, default="coldchain.db", help="SQLite database path")
    gen_p.add_argument("--output-dir", type=str, default="exports", help="Export output directory")

    # Validate
    val_p = subparsers.add_parser("validate", help="Run comprehensive data integrity checks")
    val_p.add_argument("--seed", type=int, default=20261022, help="Seed used for generation")
    val_p.add_argument("--scale", type=str, default="starter", choices=["starter", "full"], help="Dataset scale")

    # Verify
    ver_p = subparsers.add_parser("verify", help="Verify seed-based reproducibility across runs")
    ver_p.add_argument("--seed", type=int, default=20261022, help="Seed to test")

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "verify":
        cmd_verify(args)
    else:
        # Default action: run generate starter
        args.seed = 20261022
        args.scale = "starter"
        args.export = "csv,json,sql"
        args.db = "coldchain.db"
        args.output_dir = "exports"
        cmd_generate(args)


if __name__ == "__main__":
    main()
