"""Sensor API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database import get_db
from app.models import Sensor, SensorZoneMapping, SensorReading
from app.schemas import SensorOut, SensorZoneMappingOut

router = APIRouter()


@router.get("/", response_model=list[SensorOut])
def list_sensors(
    zone_id: int | None = Query(None),
    sensor_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Sensor)
    if zone_id:
        query = query.filter(Sensor.zone_id == zone_id)
    if sensor_type:
        query = query.filter(Sensor.sensor_type == sensor_type)
    if status:
        query = query.filter(Sensor.status == status)
    sensors = query.order_by(Sensor.id).offset(offset).limit(limit).all()

    result = []
    for s in sensors:
        mc = db.query(func.count(SensorZoneMapping.id)).filter(
            SensorZoneMapping.sensor_id == s.id).scalar()
        result.append({
            "id": s.id, "zone_id": s.zone_id, "sensor_type": s.sensor_type,
            "status": s.status, "manufacturer": s.manufacturer,
            "model": s.model, "installed_at": s.installed_at,
            "last_calibrated_at": s.last_calibrated_at,
            "zone_mappings_count": mc,
        })
    return result


@router.get("/{sensor_id}", response_model=SensorOut)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    s = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sensor not found")
    mc = db.query(func.count(SensorZoneMapping.id)).filter(
        SensorZoneMapping.sensor_id == s.id).scalar()
    return {
        "id": s.id, "zone_id": s.zone_id, "sensor_type": s.sensor_type,
        "status": s.status, "manufacturer": s.manufacturer,
        "model": s.model, "installed_at": s.installed_at,
        "last_calibrated_at": s.last_calibrated_at,
        "zone_mappings_count": mc,
    }


@router.get("/{sensor_id}/zone-mappings", response_model=list[SensorZoneMappingOut])
def get_sensor_mappings(sensor_id: int, db: Session = Depends(get_db)):
    mappings = db.query(SensorZoneMapping).filter(
        SensorZoneMapping.sensor_id == sensor_id).all()
    return mappings


@router.get("/{sensor_id}/readings")
def get_sensor_readings(
    sensor_id: int,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    readings = db.query(SensorReading).filter(
        SensorReading.sensor_id == sensor_id
    ).order_by(SensorReading.reading_timestamp.desc()).offset(offset).limit(limit).all()
    return readings
