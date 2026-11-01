# Prompt History

## Prompt 1 — Initial Project Request

**User:**
Build a complete, functional, professional-grade project named **WarehouseGuard AI – Intelligent Warehouse Monitoring & Risk Management System**.

Key requirements:
- Frontend: React.js with Tailwind CSS
- Backend: Python with FastAPI
- Database: PostgreSQL or SQLite
- Data Processing: Pandas and NumPy
- Charts: Recharts or Plotly
- Testing: Pytest
- Fixed seed: 20261022
- Entities: Warehouse, Zone, Sensor, SensorReading, DoorEvent, InventoryLot, StorageRequirement, Alarm, Inspection, Remediation
- Full dataset: 10 warehouses, 100 zones, 500 sensors, 1M readings, 10K inventory lots
- Anomaly detection: temperature/humidity violations, prolonged door open, abnormal occupancy, missing readings, sensor drift, incompatible inventory
- Four negative scenarios: incompatible zone, multi-zone sensor, missing readings treated as normal, alarm without inventory link
- Ground truth labels separate from detection logic
- Dashboard with KPIs, charts, filters
- Analytics: compliance rate, precision/recall/F1, MTTA/MTTR
- Validation: PKs, FKs, duplicates, allowed values, date ordering, lifecycle transitions
- CSV/JSON exports, data dictionary, schema docs
- Reproducibility verification

**AI Response:**
Built the complete project in stages:
1. Backend models, database, data generator, anomaly detection, analytics, validation
2. FastAPI routers for all entities + analytics + validation + exports
3. React frontend with 10 dashboard pages
4. Pytest test suite (6 test files)
5. Documentation (README, AI_USAGE, PROMPT_HISTORY, data dictionary)

## Prompt 2 — Simplification

**User:**
Make it simple not too complex, edit it and complete the project soon.

**AI Response:**
Completed remaining files (test_api.py, test_negative_scenarios.py, .gitignore, README, AI_USAGE, PROMPT_HISTORY) and ran the full test suite to verify everything works.
