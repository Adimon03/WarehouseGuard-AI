"""Remediation API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Remediation, Alarm
from app.schemas import RemediationOut, RemediationCreate

router = APIRouter()


@router.get("/")
def list_remediations(
    alarm_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = []
    params: dict = {"limit": limit, "offset": offset}
    if alarm_id:
        where.append("r.alarm_id = :alarm_id")
        params["alarm_id"] = alarm_id
    if status:
        where.append("r.status = :status")
        params["status"] = status
    where_clause = " AND ".join(where) if where else "1=1"

    total = db.execute(text(f"SELECT COUNT(*) FROM remediations r WHERE {where_clause}"), params).scalar()
    rows = db.execute(text(f"""
        SELECT r.id, r.alarm_id, r.inspection_id, r.action_type,
               r.description, r.performed_by, r.performed_at, r.status,
               r.created_at, a.alarm_type, a.severity
        FROM remediations r
        LEFT JOIN alarms a ON r.alarm_id = a.id
        WHERE {where_clause}
        ORDER BY r.id DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": [{"id": r[0], "alarm_id": r[1], "inspection_id": r[2],
                  "action_type": r[3], "description": r[4],
                  "performed_by": r[5],
                  "performed_at": str(r[6]), "status": r[7],
                  "created_at": str(r[8]), "alarm_type": r[9],
                  "severity": r[10]} for r in rows],
    }


@router.get("/{remediation_id}", response_model=RemediationOut)
def get_remediation(remediation_id: int, db: Session = Depends(get_db)):
    rem = db.query(Remediation).filter(Remediation.id == remediation_id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    return rem


@router.post("/", response_model=RemediationOut)
def create_remediation(body: RemediationCreate, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == body.alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    max_id = db.query(Remediation).order_by(Remediation.id.desc()).first()
    new_id = (max_id.id + 1) if max_id else 1
    rem = Remediation(
        id=new_id, alarm_id=body.alarm_id,
        inspection_id=body.inspection_id,
        action_type=body.action_type, description=body.description,
        performed_by=body.performed_by, performed_at=body.performed_at,
        status=body.status,
    )
    db.add(rem)
    db.commit()
    db.refresh(rem)
    return rem


@router.post("/{remediation_id}/complete")
def complete_remediation(remediation_id: int, db: Session = Depends(get_db)):
    rem = db.query(Remediation).filter(Remediation.id == remediation_id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    rem.status = "completed"
    db.commit()
    return {"message": "Remediation completed", "remediation_id": remediation_id}
