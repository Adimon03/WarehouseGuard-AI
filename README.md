# WarehouseGuard AI

**Intelligent Warehouse Monitoring & Risk Management System**

An end-to-end warehouse monitoring platform that tracks temperature, humidity, occupancy, door events and sensor health across warehouse zones. Automatically detects abnormal conditions, identifies affected inventory lots, generates risk alerts and recommends inspections and remediation actions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, Tailwind CSS, Recharts |
| Backend | Python, FastAPI |
| Database | SQLite (PostgreSQL-compatible SQLAlchemy ORM) |
| Data Processing | Pandas, NumPy |
| Testing | Pytest |

## Project Structure

```
warehouseguard-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── database.py          # DB engine & session
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic API schemas
│   │   ├── data_generator.py    # Synthetic data generator (seed: 20261022)
│   │   ├── anomaly_detection.py # Rule-based anomaly detection
│   │   ├── analytics.py         # KPIs, trends, alert metrics
│   │   ├── validation.py        # Data quality & validation checks
│   │   └── routers/             # REST API route modules
│   ├── tests/                   # Pytest test suite
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # API client
│   │   ├── components/           # Shared UI components
│   │   └── pages/               # Dashboard pages
│   ├── package.json
│   └── vite.config.js
├── data/                        # Generated SQLite DB
├── docs/                        # Data dictionary & schema
├── README.md
├── AI_USAGE.md
└── PROMPT_HISTORY.md
```

## Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Generate starter dataset and run detection
python -c "
import sys; sys.path.insert(0, '.')
from app.database import SessionLocal
from app.data_generator import generate_dataset
from app.anomaly_detection import run_detection
db = SessionLocal()
generate_dataset(db, full=False)  # full=True for 1M readings
run_detection(db)
print('Done!')
"

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to view the dashboard.

### 3. Using the API

The API is available at http://localhost:8000. Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/system/generate?full=true` | Generate full dataset (1M readings) |
| POST | `/api/system/generate?full=false` | Generate starter dataset |
| POST | `/api/system/detect` | Run anomaly detection |
| POST | `/api/system/generate-and-detect` | Generate + detect in one call |
| GET | `/api/system/status` | Check data status |
| GET | `/api/analytics/kpis` | Executive KPIs |
| GET | `/api/alarms/` | List alarms (with filters) |
| GET | `/api/validation/report` | Validation report |
| GET | `/api/exports/csv/{table}` | Export table as CSV |
| GET | `/api/system/data-dictionary` | Data dictionary |

Interactive API docs at http://localhost:8000/docs

## Dataset

Generated with a fixed seed of **20261022** for full reproducibility.

| Entity | Full Dataset | Starter Dataset |
|--------|-------------|-----------------|
| Warehouses | 10 | 3 |
| Zones | 100 | 15 |
| Sensors | 500 | 45 |
| Sensor Readings | 1,000,000 | 18,000 |
| Inventory Lots | 10,000 | 500 |

## Anomaly Detection

The system detects:
- Temperature and humidity violations (vs zone limits)
- Prolonged door-open events (>30 minutes)
- Abnormal occupancy (exceeds zone max)
- Missing sensor readings / sensor outages (NOT treated as normal)
- Sensor drift (gradual baseline deviation)
- Inventory assigned to incompatible zones

Each alarm is linked to affected inventory lots based on zone and time overlap.

## Four Negative Scenarios

1. **Inventory in incompatible zone** — detected by anomaly detection and validation
2. **Sensor mapped to multiple zones without justification** — detected by validation
3. **Missing readings treated as normal** — detection generates `sensor_outage` alarms
4. **Alarm not linked to affected inventory** — detected by validation

## Analytics & Validation

- Environmental compliance rate
- Sensor availability and missing-reading percentage
- Alert precision, recall, F1-score (vs ground truth)
- Mean time to acknowledge/resolve
- Automated validation for PKs, FKs, duplicates, allowed values, date ordering, lifecycle transitions

## Testing

```bash
cd backend
pytest
```

Test coverage: data generation, referential integrity, reproducibility, anomaly detection, inventory impact, alert generation, API endpoints, and negative scenarios.

## License

This project is for educational/demonstration purposes.
