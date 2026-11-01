# AI Usage Documentation

## AI Tool Used

**Kiro** — an AI-powered development environment.

## How AI Was Used

### 1. Architecture & Scaffolding
The AI assistant was used to design the overall project architecture (React + FastAPI + SQLite + SQLAlchemy) and scaffold the directory structure.

### 2. Backend Development
- SQLAlchemy ORM models for all 13 entities
- Synthetic data generator with fixed seed (20261022) producing 1M readings
- Rule-based anomaly detection (temperature, humidity, door, occupancy, outages, drift, incompatible inventory)
- Analytics module with KPIs, trends, and precision/recall/F1 metrics
- Automated validation covering PKs, FKs, duplicates, allowed values, date ordering, lifecycle transitions
- 13 REST API routers with filtering, pagination, and CSV/JSON exports

### 3. Frontend Development
- React dashboard with Tailwind CSS and Recharts
- 10 pages: Dashboard, Warehouses, Zones, Sensors, Alarms, Inventory, Inspections, Remediations, Analytics, Validation
- API client with full endpoint coverage
- Sidebar navigation and responsive layout

### 4. Testing
- Pytest test suite covering data generation, detection, inventory impact, alerts, API, and negative scenarios

### 5. Documentation
- README with setup and usage instructions
- Data dictionary and schema documentation
- This AI usage file and prompt history

## Modifications Made by Human

- Reviewed and validated all generated code
- Verified data generation produces correct row counts
- Confirmed all four negative scenarios are correctly detected
- Ensured no credentials are exposed
- Validated reproducibility (same seed → same output)

## Validation Steps Performed

1. Generated starter dataset and verified row counts (3 warehouses, 15 zones, 45 sensors, 18K readings, 500 lots)
2. Ran anomaly detection and verified alarm types match injected anomalies
3. Ran validation and confirmed all 4 negative scenarios are flagged
4. Ran pytest test suite — all tests pass
5. Started backend server and verified API endpoints respond correctly
6. Started frontend and verified dashboard renders with real data
