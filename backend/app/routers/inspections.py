"""Inspection API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Inspection, Alarm
from app.schemas import InspectionOut, InspectionCreate

router = APIRouter()


@router.get("/")
def list_inspections(
    alarm_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = []
    params: dict = {"limit": limit, "offset": offset}
    if alarm_id:
        where.append("i.alarm_id = :alarm_id")
        params["alarm_id"] = alarm_id
    if status:
        where.append("i.status = :status")
        params["status"] = status
    where_clause = " AND ".join(where) if where else "1=1"

    total = db.execute(text(f"SELECT COUNT(*) FROM inspections i WHERE {where_clause}"), params).scalar()
    rows = db.execute(text(f"""
        SELECT i.id, i.alarm_id, i.inspector_name, i.inspection_timestamp,
               i.status, i.findings, i.notes, i.created_at,
               a.alarm_type, a.severity
        FROM inspections i
        LEFT JOIN alarms a ON i.alarm_id = a.id
        WHERE {where_clause}
        ORDER BY i.id DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": [{"id": r[0], "alarm_id": r[1], "inspector_name": r[2],
                  "inspection_timestamp": str(r[3]), "status": r[4],
                  "findings": r[5], "notes": r[6],
                  "created_at": str(r[7]), "alarm_type": r[8],
                  "severity": r[9]} for r in rows],
    }


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return insp


@router.post("/", response_model=InspectionOut)
def create_inspection(body: InspectionCreate, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == body.alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    max_id = db.query(Inspection).order_by(Inspection.id.desc()).first()
    new_id = (max_id.id + 1) if max_id else 1
    insp = Inspection(
        id=new_id, alarm_id=body.alarm_id,
        inspector_name=body.inspector_name,
        inspection_timestamp=body.inspection_timestamp,
        status=body.status, findings=body.findings, notes=body.notes,
    )
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


@router.post("/{inspection_id}/complete")
def complete_inspection(inspection_id: int, findings: str = "", db: Session = Depends(get_db)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    insp.status = "completed"
    insp.findings = findings
    db.commit()
    return {"message": "Inspection completed", "inspection_id": inspection_id}
