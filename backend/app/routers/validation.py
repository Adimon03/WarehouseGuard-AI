"""Validation API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.validation import run_validation

router = APIRouter()


@router.get("/report")
def validation_report(db: Session = Depends(get_db)):
    return run_validation(db)
