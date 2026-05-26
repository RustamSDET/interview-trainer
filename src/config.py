import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Connection URI
DATABASE_URL = f"sqlite:///{DB_PATH}"
