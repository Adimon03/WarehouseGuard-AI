"""Door events API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()


@router.get("/")
def list_door_events(
    zone_id: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    prolonged_only: bool = Query(False),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = []
    params: dict = {"limit": limit, "offset": offset}

    if zone_id:
        where.append("de.zone_id = :zone_id")
        params["zone_id"] = zone_id
    if start_date:
        where.append("de.event_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("de.event_timestamp <= :end_date")
        params["end_date"] = end_date
    if prolonged_only:
        where.append("de.duration_seconds > 1800")

    where_clause = " AND ".join(where) if where else "1=1"

    count_sql = f"SELECT COUNT(*) FROM door_events de WHERE {where_clause}"
    total = db.execute(text(count_sql), params).scalar()

    data_sql = f"""
        SELECT de.id, de.zone_id, de.sensor_id, de.event_timestamp,
               de.event_type, de.duration_seconds, de.is_anomaly_injected
        FROM door_events de
        WHERE {where_clause}
        ORDER BY de.event_timestamp DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(data_sql), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": [{"id": r[0], "zone_id": r[1], "sensor_id": r[2],
                  "event_timestamp": str(r[3]), "event_type": r[4],
                  "duration_seconds": r[5], "is_anomaly": bool(r[6])}
                 for r in rows],
    }
