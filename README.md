# WarehouseGuard AI

**Intelligent Warehouse Monitoring & Risk Management System**

Monitors temperature, humidity, occupancy and door events by warehouse zone and alerts on risk conditions. Generates synthetic data with a fixed seed, applies rule-based anomaly detection, identifies affected inventory, and produces validation reports with reproducibility checks.

## Quick Start

```bash
cd backend
pip install -r requirements.txt

# Generate data, run detection, export CSV/JSON, validate, check reproducibility
python run.py            # starter dataset
python run.py --full      # full dataset (1M readings, 10K lots)
```

Output files are saved to `data/` (CSV per table, ground_truth.csv/json, validation_summary.json).

## Run Tests

```bash
cd backend
pytest
```

## Run the Dashboard (optional)

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install && npm run dev
```

Open http://localhost:5173 for the dashboard, http://localhost:8000/docs for API docs.

## Data Generation

Fixed seed: **20261022**. Same seed produces identical row counts across runs (verified by `run.py`).

| Entity | Full Dataset | Starter Dataset |
|--------|-------------|-----------------|
| Warehouses | 10 | 3 |
| Zones | 100 | 15 |
| Sensors | 500 | 45 |
| Sensor Readings | 1,000,000 | 18,000 |
| Inventory Lots | 10,000 | 500 |

### ID Naming Conventions

| Entity | Format | Example |
|--------|--------|---------|
| Warehouse | WH-NNN | WH-001 |
| Zone | ZONE-WWW-NNN | ZONE-001-001 |
| Sensor | SNS-ZZZ-TYPE-NN | SNS-001-TEMP-01 |
| Reading | RDG-NNNNNNN | RDG-0000001 |
| Inventory Lot | LOT-2026-NNNNNN | LOT-2026-000001 |
| Alarm | ALM-NNNNNN | ALM-000001 |
| Inspection | INSP-NNNNNN | INSP-000001 |
| Remediation | REM-NNNNNN | REM-000001 |

## Entities & Relationships

```
Warehouse (1) → (N) Zone → (N) Sensor → (N) SensorReading
Zone → (N) DoorEvent
Zone → (N) InventoryLot
StorageRequirement ← InventoryLot.product_category
Alarm → (N:M) InventoryLot  (via AlarmInventoryLot)
Alarm → (N) Inspection
Alarm → (N) Remediation
GroundTruthAnomaly (isolated — never used by detection)
```

Cardinalities: Warehouse:Zone is 1:N, Zone:Sensor is 1:N, Alarm:InventoryLot is N:M (bridge table), Sensor:SensorReading is 1:N.

## Anomaly Detection

Rule-based detection using product-specific storage requirements:

- **Temperature/humidity violations** — readings outside zone limits
- **Prolonged door-open** — door events > 30 minutes
- **Abnormal occupancy** — exceeds zone max_occupancy
- **Sensor outages** — missing readings flagged as anomalies (NOT treated as normal)
- **Sensor drift** — gradual baseline deviation detected via quartile comparison
- **Incompatible inventory** — product category assigned to wrong zone type

Each alarm links to affected inventory lots via time + zone overlap.

## Four Negative Scenarios

1. **Lot assigned to incompatible zone** — detected by anomaly detection and validation
2. **Sensor mapped to multiple zones without rationale** — detected by validation
3. **Reading gap treated as normal** — detection generates `sensor_outage` alarms
4. **Alarm not linked to affected lots** — detected by validation

Ground-truth labels are stored separately (`ground_truth_anomalies` table, exported as `ground_truth.csv/json`) and never queried by detection logic.

## Validation

Checks: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, lifecycle transitions, duplicate detection, inventory relationships, and all four negative scenarios.

## Evaluation Metrics

- Environmental compliance rate
- Sensor availability
- Missing-reading percentage
- Alert precision, recall, F1-score (vs ground truth)
- Mean time to acknowledge/resolve

## Exports

`run.py` exports to `data/`:
- CSV per table (warehouses.csv, zones.csv, sensors.csv, sensor_readings.csv, etc.)
- `ground_truth.csv` + `ground_truth.json`
- `validation_summary.json`

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- Data Processing: NumPy, Pandas
- Frontend: React, Tailwind CSS, Recharts
- Testing: Pytest

## Project Structure

```
backend/
  app/
    models.py              # 13 SQLAlchemy ORM models
    data_generator.py     # Synthetic data generator (seed: 20261022)
    anomaly_detection.py  # Rule-based detection + alarm/inspection/remediation
    analytics.py          # KPIs, trends, precision/recall/F1
    validation.py         # PK/FK/enum/date/lifecycle validation + negative scenarios
    main.py               # FastAPI app
    routers/              # 13 REST API modules
  tests/                  # 87 Pytest tests
  run.py                  # End-to-end runner (generate → detect → export → validate)
  requirements.txt
frontend/
  src/                    # React dashboard (10 pages)
  package.json
docs/
  data_dictionary.md      # Field-level data dictionary
  schema.md               # Entity relationships
data/                     # Generated CSV/JSON exports
```
