#!/usr/bin/env python3
"""
Initialize ChatMMA database with enhanced schema.
Usage: python scripts/init_db.py [--reset]
"""
import sqlite3
import argparse
import os
from pathlib import Path

DB_PATH = "data/chatmma.db"
SCHEMA_PATH = "schema.sql"


def init_database(reset=False):
    """Initialize database with schema."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    if reset and os.path.exists(DB_PATH):
        print(f"⚠️  Resetting database: {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Read and execute schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()

    cursor.executescript(schema)
    conn.commit()

    # Verify tables created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"✓ Database initialized: {DB_PATH}")
    print(f"✓ Tables created: {', '.join(tables)}")

    conn.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="Initialize ChatMMA database")
    parser.add_argument("--reset", action="store_true", help="Reset existing database")
    args = parser.parse_args()

    init_database(reset=args.reset)


if __name__ == "__main__":
    main()
