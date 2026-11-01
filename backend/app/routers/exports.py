"""CSV / JSON export API routes."""
import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

EXPORTABLE_TABLES = [
    "warehouses", "zones", "sensors", "sensor_zone_mappings",
    "sensor_readings", "door_events", "storage_requirements",
    "inventory_lots", "alarms", "alarm_inventory_lots",
    "inspections", "remediations", "ground_truth_anomalies",
]


@router.get("/csv/{table}")
def export_csv(table: str, limit: int = 10000, db: Session = Depends(get_db)):
    if table not in EXPORTABLE_TABLES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown table. Available: {EXPORTABLE_TABLES}")

    rows = db.execute(text(f"SELECT * FROM {table} LIMIT :limit"), {"limit": limit}).fetchall()
    if not rows:
        return Response(content="", media_type="text/csv")

    columns = rows[0]._fields
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([str(v) if v is not None else "" for v in row])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}.csv"},
    )


@router.get("/json/{table}")
def export_json(table: str, limit: int = 10000, db: Session = Depends(get_db)):
    if table not in EXPORTABLE_TABLES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown table. Available: {EXPORTABLE_TABLES}")

    rows = db.execute(text(f"SELECT * FROM {table} LIMIT :limit"), {"limit": limit}).fetchall()
    if not rows:
        return []

    columns = rows[0]._fields
    data = []
    for row in rows:
        record = {}
        for i, col in enumerate(columns):
            val = row[i]
            if hasattr(val, "isoformat"):
                record[col] = val.isoformat()
            elif isinstance(val, (list, dict)):
                record[col] = val
            else:
                record[col] = val
        data.append(record)

    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={table}.json"},
    )


@router.get("/list")
def list_exportable_tables():
    return {"tables": EXPORTABLE_TABLES}
