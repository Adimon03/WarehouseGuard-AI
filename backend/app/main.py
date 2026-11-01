"""FastAPI application for WarehouseGuard AI."""
import os
import csv
import io
import json
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, init_db, DB_PATH, SessionLocal
from app import models, schemas
from app.data_generator import generate_dataset, compute_checksums
from app.anomaly_detection import run_detection
from app.analytics import (
    get_kpi_summary, get_temperature_trend, get_humidity_trend,
    get_occupancy_trend, get_door_event_stats, get_alert_metrics,
    get_alarm_distribution, get_sensor_health, get_inventory_impact,
    get_compliance_by_zone,
)
from app.validation import run_validation

from app.routers import (
    warehouses, zones, sensors, readings, door_events,
    inventory, storage_reqs, alarms, inspections, remediations,
    analytics, validation, exports,
)

app = FastAPI(
    title="WarehouseGuard AI",
    description="Intelligent Warehouse Monitoring & Risk Management System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(warehouses.router, prefix="/api/warehouses", tags=["Warehouses"])
app.include_router(zones.router, prefix="/api/zones", tags=["Zones"])
app.include_router(sensors.router, prefix="/api/sensors", tags=["Sensors"])
app.include_router(readings.router, prefix="/api/readings", tags=["Sensor Readings"])
app.include_router(door_events.router, prefix="/api/door-events", tags=["Door Events"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(storage_reqs.router, prefix="/api/storage-requirements", tags=["Storage Requirements"])
app.include_router(alarms.router, prefix="/api/alarms", tags=["Alarms"])
app.include_router(inspections.router, prefix="/api/inspections", tags=["Inspections"])
app.include_router(remediations.router, prefix="/api/remediations", tags=["Remediations"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(validation.router, prefix="/api/validation", tags=["Validation"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])


# ═══════════════════════════════════════════════════════════════════════════
#  System endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/system/status")
def system_status(db: Session = Depends(get_db)):
    """Return system status including whether data has been generated."""
    db_exists = os.path.exists(DB_PATH)
    if not db_exists:
        return {"status": "empty", "message": "Database not initialised. Run /api/system/generate."}

    counts = {}
    for t in ["warehouses", "zones", "sensors", "sensor_readings", "door_events",
              "inventory_lots", "storage_requirements", "alarms", "inspections",
              "remediations", "ground_truth_anomalies"]:
        try:
            counts[t] = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        except Exception:
            counts[t] = 0
    return {"status": "ready", "counts": counts}


@app.post("/api/system/generate")
def system_generate(full: bool = Query(True, description="Generate full (1M readings) or starter dataset"),
                     db: Session = Depends(get_db)):
    """Generate (or regenerate) the synthetic dataset."""
    summary = generate_dataset(db, full=full)
    return {"message": "Dataset generated", "summary": summary}


@app.post("/api/system/detect")
def system_detect(db: Session = Depends(get_db)):
    """Run anomaly detection on the generated data."""
    wh_count = db.execute(text("SELECT COUNT(*) FROM warehouses")).scalar()
    if wh_count == 0:
        raise HTTPException(status_code=400, detail="No data found. Run /api/system/generate first.")
    result = run_detection(db)
    return {"message": "Detection complete", "summary": result}


@app.post("/api/system/generate-and-detect")
def system_generate_and_detect(full: bool = Query(True), db: Session = Depends(get_db)):
    """Generate data and run detection in one call."""
    gen_summary = generate_dataset(db, full=full)
    det_summary = run_detection(db)
    val_report = run_validation(db)
    return {
        "generation": gen_summary,
        "detection": det_summary,
        "validation": {
            "total_checks": val_report["total_checks"],
            "passed": val_report["passed"],
            "failed": val_report["failed"],
            "warnings": val_report["warnings"],
        },
    }


@app.get("/api/system/reproducibility")
def system_reproducibility(db: Session = Depends(get_db)):
    """Verify reproducibility by computing checksums of the current dataset."""
    return compute_checksums(db)


@app.get("/api/system/data-dictionary")
def data_dictionary():
    """Return the data dictionary for all tables."""
    return DATA_DICTIONARY


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


DATA_DICTIONARY = {
    "warehouses": {
        "description": "Top-level warehouse facilities",
        "columns": {
            "id": "Primary key (int)",
            "name": "Warehouse name (str)",
            "location": "Geographic location (str)",
            "total_area_sqm": "Total area in square metres (float)",
            "manager": "Warehouse manager name (str)",
            "created_at": "Creation timestamp (datetime)",
        },
    },
    "zones": {
        "description": "Zones within a warehouse, each with environmental limits",
        "columns": {
            "id": "Primary key (int)",
            "warehouse_id": "FK to warehouses (int)",
            "name": "Zone name (str)",
            "zone_type": "ambient | cold_storage | frozen | hazardous",
            "area_sqm": "Zone area in square metres (float)",
            "max_occupancy": "Maximum allowed occupancy (int)",
            "min_temp_c": "Minimum allowed temperature (float)",
            "max_temp_c": "Maximum allowed temperature (float)",
            "min_humidity_pct": "Minimum allowed humidity (float)",
            "max_humidity_pct": "Maximum allowed humidity (float)",
        },
    },
    "sensors": {
        "description": "Sensors installed in zones to monitor conditions",
        "columns": {
            "id": "Primary key (int)",
            "zone_id": "FK to zones (int)",
            "sensor_type": "temperature | humidity | occupancy | door",
            "status": "active | drift | offline",
            "manufacturer": "Sensor manufacturer (str)",
            "model": "Sensor model (str)",
            "installed_at": "Installation date (datetime)",
            "last_calibrated_at": "Last calibration date (datetime)",
        },
    },
    "sensor_zone_mappings": {
        "description": "Tracks all zone assignments per sensor. Sensors mapped to multiple zones without justification are flagged as anomalies.",
        "columns": {
            "id": "Primary key (int)",
            "sensor_id": "FK to sensors (int)",
            "zone_id": "FK to zones (int)",
            "is_primary": "Whether this is the primary zone (bool)",
            "justification": "Reason for mapping (str, nullable — null indicates anomaly)",
            "assigned_at": "Assignment timestamp (datetime)",
        },
    },
    "sensor_readings": {
        "description": "Time-series readings from sensors (1M rows in full dataset)",
        "columns": {
            "id": "Primary key (int)",
            "sensor_id": "FK to sensors (int)",
            "reading_timestamp": "Reading timestamp (datetime)",
            "temperature_c": "Temperature in Celsius (float, nullable for non-temp sensors)",
            "humidity_pct": "Humidity percentage (float, nullable for non-humidity sensors)",
            "occupancy_count": "Occupancy count (int, nullable for non-occupancy sensors)",
            "door_state": "open | closed (str, nullable for non-door sensors)",
            "is_missing": "Whether this reading represents a sensor outage (bool)",
            "is_anomaly_injected": "Internal flag for ground truth (bool, NOT used by detection)",
        },
    },
    "door_events": {
        "description": "Door open/close events",
        "columns": {
            "id": "Primary key (int)",
            "zone_id": "FK to zones (int)",
            "sensor_id": "FK to sensors (int)",
            "event_timestamp": "Event timestamp (datetime)",
            "event_type": "open | close",
            "duration_seconds": "Duration the door was open (float)",
            "is_anomaly_injected": "Internal flag for ground truth (bool)",
        },
    },
    "storage_requirements": {
        "description": "Product-specific storage requirements per category",
        "columns": {
            "id": "Primary key (int)",
            "product_category": "Product category (str, unique)",
            "min_temp_c": "Minimum storage temperature (float)",
            "max_temp_c": "Maximum storage temperature (float)",
            "min_humidity_pct": "Minimum storage humidity (float)",
            "max_humidity_pct": "Maximum storage humidity (float)",
            "dwell_time_limit_days": "Maximum dwell time in days (int)",
            "compatible_zone_types": "JSON array of compatible zone types",
        },
    },
    "inventory_lots": {
        "description": "Inventory lots stored in warehouse zones",
        "columns": {
            "id": "Primary key (int)",
            "zone_id": "FK to zones (int)",
            "product_name": "Product name (str)",
            "product_category": "Product category (str)",
            "quantity": "Quantity (int)",
            "unit": "Unit of measure (str)",
            "batch_number": "Batch identifier (str)",
            "arrival_date": "Arrival timestamp (datetime)",
            "departure_date": "Departure timestamp (datetime, nullable if still stored)",
            "status": "stored | departed | expired",
        },
    },
    "alarms": {
        "description": "Anomaly alarms generated by detection or manually created",
        "columns": {
            "id": "Primary key (int)",
            "alarm_type": "temperature_violation | humidity_violation | prolonged_door_open | abnormal_occupancy | sensor_outage | sensor_drift | inventory_incompatible_zone",
            "severity": "critical | warning | info",
            "zone_id": "FK to zones (int)",
            "sensor_id": "FK to sensors (int, nullable)",
            "start_timestamp": "Alarm start (datetime)",
            "end_timestamp": "Alarm end (datetime, nullable if ongoing)",
            "description": "Human-readable alarm description (text)",
            "recommended_action": "Recommended remediation action (text)",
            "status": "active | acknowledged | resolved",
            "source": "preexisting | detection",
            "acknowledged_at": "Acknowledgement timestamp (datetime, nullable)",
            "acknowledged_by": "Who acknowledged (str, nullable)",
            "resolved_at": "Resolution timestamp (datetime, nullable)",
            "resolved_by": "Who resolved (str, nullable)",
        },
    },
    "alarm_inventory_lots": {
        "description": "Junction table linking alarms to affected inventory lots",
        "columns": {
            "id": "Primary key (int)",
            "alarm_id": "FK to alarms (int)",
            "inventory_lot_id": "FK to inventory_lots (int)",
        },
    },
    "inspections": {
        "description": "Inspection records for alarms",
        "columns": {
            "id": "Primary key (int)",
            "alarm_id": "FK to alarms (int)",
            "inspector_name": "Inspector name (str)",
            "inspection_timestamp": "Scheduled/actual inspection time (datetime)",
            "status": "pending | scheduled | completed | cancelled",
            "findings": "Inspection findings (text, nullable)",
            "notes": "Additional notes (text, nullable)",
        },
    },
    "remediations": {
        "description": "Remediation actions for alarms",
        "columns": {
            "id": "Primary key (int)",
            "alarm_id": "FK to alarms (int)",
            "inspection_id": "FK to inspections (int, nullable)",
            "action_type": "adjust_temperature | relocate_inventory | recalibrate_sensor | replace_sensor | schedule_inspection | manual_review",
            "description": "Remediation description (text)",
            "performed_by": "Who performed the action (str)",
            "performed_at": "When performed (datetime)",
            "status": "pending | in_progress | completed",
        },
    },
    "ground_truth_anomalies": {
        "description": "Ground-truth labels for known anomalies. NEVER queried by detection logic — used only for evaluation metrics.",
        "columns": {
            "id": "Primary key (int)",
            "anomaly_type": "Type of anomaly (str)",
            "entity_type": "sensor_reading | door_event | sensor | inventory_lot | alarm",
            "entity_id": "ID of the affected entity (int)",
            "description": "Description of the anomaly (text)",
            "true_severity": "critical | warning | info",
            "injected_at": "When the anomaly was injected (datetime)",
        },
    },
}
