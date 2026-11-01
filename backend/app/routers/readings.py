"""Sensor readings API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import SensorReading

router = APIRouter()


@router.get("/")
def list_readings(
    sensor_id: int | None = Query(None),
    zone_id: int | None = Query(None),
    is_missing: bool | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(100, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = []
    params: dict = {"limit": limit, "offset": offset}

    if sensor_id:
        where.append("sr.sensor_id = :sensor_id")
        params["sensor_id"] = sensor_id
    if zone_id:
        where.append("s.zone_id = :zone_id")
        params["zone_id"] = zone_id
    if is_missing is not None:
        where.append("sr.is_missing = :is_missing")
        params["is_missing"] = 1 if is_missing else 0
    if start_date:
        where.append("sr.reading_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("sr.reading_timestamp <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(where) if where else "1=1"

    count_sql = f"""
        SELECT COUNT(*) FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE {where_clause}
    """
    total = db.execute(text(count_sql), params).scalar()

    data_sql = f"""
        SELECT sr.id, sr.sensor_id, sr.reading_timestamp, sr.temperature_c,
               sr.humidity_pct, sr.occupancy_count, sr.door_state, sr.is_missing
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE {where_clause}
        ORDER BY sr.reading_timestamp DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(data_sql), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": [{"id": r[0], "sensor_id": r[1], "reading_timestamp": str(r[2]),
                  "temperature_c": r[3], "humidity_pct": r[4],
                  "occupancy_count": r[5], "door_state": r[6], "is_missing": bool(r[7])}
                 for r in rows],
    }
