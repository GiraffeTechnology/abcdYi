"""Initialize the database — create all tables."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
from src.db.session import engine
import src.db.models  # noqa: F401


def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print(f"  Created {len(Base.metadata.tables)} tables:")
    for table_name in sorted(Base.metadata.tables.keys()):
        print(f"    - {table_name}")
    print("Database initialization complete.")


if __name__ == "__main__":
    init_db()
