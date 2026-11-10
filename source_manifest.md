# 📜 ColdChain Sentinel — Source Code & Artifact Manifest

**System Version:** 1.0.0  
**Deterministic Random Seed:** `20261022`  
**Sampling Cadence:** 10 Minutes  
**License:** Public Domain / Synthetic Regulatory Simulation  
**Generated Timestamp:** 2026-11-10T12:25:00Z  

---

## 1. Project Directory & Artifact Inventory

| Category | File Path | Description |
| :--- | :--- | :--- |
| **User Interface** | `app.py` | Interactive Streamlit Web Hub with 5 tailored actor persona workspaces |
| **Command Line Interface** | `cli.py` | Unified CLI supporting `generate`, `validate`, and `verify` commands |
| **Core Models** | `coldchain/models.py` | Pydantic and dataclass models for 10 entities, bridge tables, and ground truth |
| **Telemetry & Physics** | `coldchain/compliance.py` | Arrhenius MKT calculations, excursion detection, evidence hashing, and CAPA engine |
| **Synthetic Generator** | `coldchain/generator.py` | Deterministic synthetic generator with controlled edge-case injection |
| **Database & Persistence** | `coldchain/db.py` | SQLite schema, foreign keys, indexing, and multi-format CSV/JSON exporters |
| **Validation Battery** | `coldchain/validator.py` | Automated 8-point relational, arithmetic, and benchmark validation suite |
| **Reproducibility Test** | `coldchain/verify_reproducibility.py`| Dual-run bit-exact hash verification across all entities |
| **Automated Tests** | `tests/test_coldchain.py` | Pytest suite validating MKT physics, unassigned logger detection, and keys |
| **Database File** | `coldchain.db` | Indexed SQLite database with all tables, views, and foreign key enforcement |
| **Documentation** | `README.md` | Executive pitch, architecture overview, and quickstart instructions |
| **Documentation** | `database_UML.md` | Complete Mermaid ERD, UML Class diagram, and schema matrix |
| **Documentation** | `validation_summary.md`| Zero-defect validation audit report across 8 dimensions |
| **Documentation** | `architecture.md` | System architecture blueprint, sequence diagrams, and 21 CFR Part 11 design |
| **Documentation** | `subject_guide.md` | Biopharma cold chain subject guide (USP <1079>, MKT physics, packaging) |
| **Documentation** | `data_dictionary.md` | Granular data dictionary with validation rules for all fields |

---

## 2. Relational Seed Data Archive Mapping

| Entity Name | Primary Key | CSV Export Path | JSON Export Path | Row Count | SHA-256 Checksum (Seed 20261022) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`products`** | `product_id` | `exports/csv/products.csv` | `exports/json/products.json` | 6 | `8b12063bea95b1e1...` |
| **`packagings`** | `packaging_id` | `exports/csv/packagings.csv` | `exports/json/packagings.json` | 4 | `6d77dadeb542ad2b...` |
| **`policies`** | `policy_id` | `exports/csv/policies.csv` | `exports/json/policies.json` | 6 | `46a3d44056cd4f83...` |
| **`lots`** | `lot_id` | `exports/csv/lots.csv` | `exports/json/lots.json` | 12 | `fa22b41631a9519a...` |
| **`loggers`** | `logger_id` | `exports/csv/loggers.csv` | `exports/json/loggers.json` | 100 | `74d066ea9c118db9...` |
| **`shipments`** | `shipment_id` | `exports/csv/shipments.csv` | `exports/json/shipments.json` | 50 | `9f02e6d0db450acd...` |
| **`shipment_lots`** | `bridge_id` | `exports/csv/shipment_lots.csv` | `exports/json/shipment_lots.json` | 50 | `068013683479853a...` |
| **`route_stops`** | `stop_id` | `exports/csv/route_stops.csv` | `exports/json/route_stops.json` | 150 | `f627f9efe248ca5f...` |
| **`custody_events`**| `custody_id` | `exports/csv/custody_events.csv`| `exports/json/custody_events.json`| 150 | `b5da494598aa9521...` |
| **`temperature_readings`**| `reading_id` | `exports/csv/temperature_readings.csv`| `exports/json/temperature_readings.json`| 12,563 | `402f1329d2908675...` |
| **`excursion_reports`** | `report_id` | `exports/csv/excursion_reports.csv` | `exports/json/excursion_reports.json` | 50 | `50477199e45690e7...` |
| **`ground_truth`** | `anomaly_id` | `exports/csv/ground_truth.csv` | `exports/json/ground_truth.json` | 50 | `ec6306ebe107a24b...` |

---

## 3. Standard Execution Commands

```bash
# 1. Run Unit Tests (Pytest)
python -m pytest -v

# 2. Generate Dataset (Starter Scale)
python cli.py generate --seed 20261022 --scale starter --export csv,json,sql

# 3. Generate Dataset (Full Scale 5,000 Shipments)
python cli.py generate --seed 20261022 --scale full --export csv,json,sql

# 4. Run Automated 8-Point Validation Suite
python cli.py validate

# 5. Verify Dual-Run Bit-Exact Reproducibility
python cli.py verify --seed 20261022

# 6. Launch the Interactive Web Dashboard
python -m streamlit run app.py
```

---

## 4. Public Provenance & Legal Guidance
- **Data Source:** 100% Synthetic Data generated algorithmically using mathematical random walk processes, Arrhenius kinetic degradation curves, and standard physical thermal packaging properties.
- **Standards Cited:** United States Pharmacopeia USP General Chapter <1079>, U.S. FDA 21 CFR Part 11, European Commission Guidelines on Good Distribution Practice (GDP 2013/C 343/01), and WHO Technical Report Series No. 961.
- **Privacy & IP:** No proprietary, clinical trial, or personally identifiable data is used or stored.
