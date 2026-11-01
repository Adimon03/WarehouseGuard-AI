"""Alarm API routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import get_db
from app.models import Alarm, AlarmInventoryLot, Zone, InventoryLot, Inspection, Remediation
from app.schemas import AlarmOut, AlarmAcknowledge, AlarmResolve

router = APIRouter()


@router.get("/")
def list_alarms(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    alarm_type: str | None = Query(None),
    zone_id: int | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if severity:
        where.append("a.severity = :severity")
        params["severity"] = severity
    if status:
        where.append("a.status = :status")
        params["status"] = status
    if alarm_type:
        where.append("a.alarm_type = :alarm_type")
        params["alarm_type"] = alarm_type
    if zone_id:
        where.append("a.zone_id = :zone_id")
        params["zone_id"] = zone_id
    if source:
        where.append("a.source = :source")
        params["source"] = source

    where_clause = " AND ".join(where)

    count_sql = f"SELECT COUNT(*) FROM alarms a WHERE {where_clause}"
    total = db.execute(text(count_sql), params).scalar()

    data_sql = f"""
        SELECT a.id, a.alarm_type, a.severity, a.zone_id, a.sensor_id,
               a.start_timestamp, a.end_timestamp, a.description,
               a.recommended_action, a.status, a.source,
               a.acknowledged_at, a.acknowledged_by,
               a.resolved_at, a.resolved_by, a.created_at,
               z.name as zone_name
        FROM alarms a
        LEFT JOIN zones z ON a.zone_id = z.id
        WHERE {where_clause}
        ORDER BY a.start_timestamp DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(data_sql), params).fetchall()

    data = []
    for r in rows:
        alarm_id = r[0]
        inv_ids = [row[0] for row in db.execute(text(
            "SELECT inventory_lot_id FROM alarm_inventory_lots WHERE alarm_id = :aid"
        ), {"aid": alarm_id}).fetchall()]
        data.append({
            "id": alarm_id, "alarm_type": r[1], "severity": r[2],
            "zone_id": r[3], "sensor_id": r[4],
            "start_timestamp": str(r[5]) if r[5] else None,
            "end_timestamp": str(r[6]) if r[6] else None,
            "description": r[7], "recommended_action": r[8],
            "status": r[9], "source": r[10],
            "acknowledged_at": str(r[11]) if r[11] else None,
            "acknowledged_by": r[12],
            "resolved_at": str(r[13]) if r[13] else None,
            "resolved_by": r[14],
            "created_at": str(r[15]) if r[15] else None,
            "zone_name": r[16],
            "affected_inventory_ids": inv_ids,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": data,
    }


@router.get("/{alarm_id}")
def get_alarm(alarm_id: int, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    zone = db.query(Zone).filter(Zone.id == alarm.zone_id).first()
    inv_ids = [ail.inventory_lot_id for ail in db.query(AlarmInventoryLot).filter(
        AlarmInventoryLot.alarm_id == alarm_id).all()]
    inspections = db.query(Inspection).filter(Inspection.alarm_id == alarm_id).all()
    remediations = db.query(Remediation).filter(Remediation.alarm_id == alarm_id).all()

    return {
        "id": alarm.id, "alarm_type": alarm.alarm_type, "severity": alarm.severity,
        "zone_id": alarm.zone_id, "sensor_id": alarm.sensor_id,
        "start_timestamp": str(alarm.start_timestamp),
        "end_timestamp": str(alarm.end_timestamp) if alarm.end_timestamp else None,
        "description": alarm.description,
        "recommended_action": alarm.recommended_action,
        "status": alarm.status, "source": alarm.source,
        "acknowledged_at": str(alarm.acknowledged_at) if alarm.acknowledged_at else None,
        "acknowledged_by": alarm.acknowledged_by,
        "resolved_at": str(alarm.resolved_at) if alarm.resolved_at else None,
        "resolved_by": alarm.resolved_by,
        "created_at": str(alarm.created_at),
        "zone_name": zone.name if zone else None,
        "affected_inventory_ids": inv_ids,
        "inspections": [{"id": i.id, "inspector_name": i.inspector_name,
                         "status": i.status, "findings": i.findings}
                        for i in inspections],
        "remediations": [{"id": r.id, "action_type": r.action_type,
                         "status": r.status, "description": r.description}
                        for r in remediations],
    }


@router.post("/{alarm_id}/acknowledge")
def acknowledge_alarm(alarm_id: int, body: AlarmAcknowledge = Body(default=AlarmAcknowledge()),
                      db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    alarm.status = "acknowledged"
    alarm.acknowledged_at = datetime.utcnow()
    alarm.acknowledged_by = body.acknowledged_by
    db.commit()
    return {"message": "Alarm acknowledged", "alarm_id": alarm_id}


@router.post("/{alarm_id}/resolve")
def resolve_alarm(alarm_id: int, body: AlarmResolve = Body(default=AlarmResolve()),
                  db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    alarm.status = "resolved"
    alarm.resolved_at = datetime.utcnow()
    alarm.resolved_by = body.resolved_by
    if not alarm.acknowledged_at:
        alarm.acknowledged_at = datetime.utcnow()
        alarm.acknowledged_by = body.resolved_by
    db.commit()
    return {"message": "Alarm resolved", "alarm_id": alarm_id}
