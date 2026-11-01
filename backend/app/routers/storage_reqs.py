"""Storage requirements API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import StorageRequirement
from app.schemas import StorageRequirementOut

router = APIRouter()


@router.get("/", response_model=list[StorageRequirementOut])
def list_storage_requirements(db: Session = Depends(get_db)):
    return db.query(StorageRequirement).order_by(StorageRequirement.id).all()
