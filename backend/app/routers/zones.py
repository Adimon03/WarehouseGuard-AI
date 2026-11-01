"""Zone API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database import get_db
from app.models import Zone, Sensor, InventoryLot
from app.schemas import ZoneOut

router = APIRouter()


@router.get("/", response_model=list[ZoneOut])
def list_zones(
    warehouse_id: int | None = Query(None),
    zone_type: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Zone)
    if warehouse_id:
        query = query.filter(Zone.warehouse_id == warehouse_id)
    if zone_type:
        query = query.filter(Zone.zone_type == zone_type)
    zones = query.order_by(Zone.id).offset(offset).limit(limit).all()

    result = []
    for z in zones:
        sc = db.query(func.count(Sensor.id)).filter(Sensor.zone_id == z.id).scalar()
        ic = db.query(func.count(InventoryLot.id)).filter(InventoryLot.zone_id == z.id).scalar()
        result.append({
            "id": z.id, "warehouse_id": z.warehouse_id, "name": z.name,
            "zone_type": z.zone_type, "area_sqm": z.area_sqm,
            "max_occupancy": z.max_occupancy,
            "min_temp_c": z.min_temp_c, "max_temp_c": z.max_temp_c,
            "min_humidity_pct": z.min_humidity_pct,
            "max_humidity_pct": z.max_humidity_pct,
            "sensor_count": sc, "inventory_count": ic,
        })
    return result


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    z = db.query(Zone).filter(Zone.id == zone_id).first()
    if not z:
        raise HTTPException(status_code=404, detail="Zone not found")
    sc = db.query(func.count(Sensor.id)).filter(Sensor.zone_id == z.id).scalar()
    ic = db.query(func.count(InventoryLot.id)).filter(InventoryLot.zone_id == z.id).scalar()
    return {
        "id": z.id, "warehouse_id": z.warehouse_id, "name": z.name,
        "zone_type": z.zone_type, "area_sqm": z.area_sqm,
        "max_occupancy": z.max_occupancy,
        "min_temp_c": z.min_temp_c, "max_temp_c": z.max_temp_c,
        "min_humidity_pct": z.min_humidity_pct,
        "max_humidity_pct": z.max_humidity_pct,
        "sensor_count": sc, "inventory_count": ic,
    }
