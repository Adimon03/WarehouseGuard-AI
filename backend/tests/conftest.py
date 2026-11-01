"""Pytest configuration and fixtures.

Sets up an isolated test database with the starter dataset and detection
results so every test has consistent data to work with.
"""
import os
import sys
import tempfile

# Set test DB path BEFORE any app imports
_TEST_DB = os.path.join(tempfile.gettempdir(), "wg_test.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["WAREHOUSEGUARD_DB_PATH"] = _TEST_DB

# Ensure backend dir is on the path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import pytest
from app.database import SessionLocal, reset_db
from app.data_generator import generate_dataset
from app.anomaly_detection import run_detection


@pytest.fixture(scope="session")
def db_session():
    """Session-scoped fixture: generates starter data + runs detection once."""
    db = SessionLocal()
    # Generate starter dataset (smaller, faster for tests)
    generate_dataset(db, full=False)
    # Run anomaly detection
    run_detection(db)
    yield db
    db.close()
    from app.database import engine
    engine.dispose()
    if os.path.exists(_TEST_DB):
        try:
            os.remove(_TEST_DB)
        except PermissionError:
            pass


@pytest.fixture(scope="session")
def detected_summary(db_session):
    """Re-run detection and return the summary (for tests that need it)."""
    from app.anomaly_detection import run_detection
    return run_detection(db_session)
