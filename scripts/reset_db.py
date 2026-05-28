"""Reset the database — drop all tables and recreate."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
from src.db.session import engine
import src.db.models  # noqa: F401


def reset_db():
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    print("  All tables dropped.")
    Base.metadata.create_all(bind=engine)
    print(f"  Recreated {len(Base.metadata.tables)} tables.")
    print("Database reset complete.")


if __name__ == "__main__":
    reset_db()
