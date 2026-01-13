"""
Initialize SQLite database for ChatMMA
Run this once to set up the database schema
"""
import sqlite3
import sys
import os
sys.path.append(os.path.dirname(__file__))
from utils import load_config, log

def init_database():
    """Create all database tables"""
    config = load_config()
    db_path = config['database']['path']

    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        date DATE NOT NULL,
        location TEXT,
        fights_count INTEGER,
        results_entered BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Fights table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        fighter_a TEXT NOT NULL,
        fighter_b TEXT NOT NULL,
        weight_class TEXT,
        is_main_card BOOLEAN DEFAULT 0,
        scheduled_rounds INTEGER,
        result TEXT,
        method TEXT,
        round INTEGER,
        time TEXT,
        FOREIGN KEY (event_id) REFERENCES events(id)
    )
    ''')

    # Sources table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        publication TEXT,
        analyst TEXT,
        url TEXT,
        credibility_score REAL DEFAULT 50.0,
        total_predictions INTEGER DEFAULT 0,
        correct_predictions INTEGER DEFAULT 0,
        accuracy_rate REAL DEFAULT 0.0
    )
    ''')

    # Predictions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fight_id INTEGER NOT NULL,
        source_id INTEGER NOT NULL,
        event_name TEXT NOT NULL,
        prediction TEXT NOT NULL,
        method TEXT,
        analyst_confidence TEXT,
        extraction_confidence REAL,
        reasoning TEXT,
        dfs_note TEXT,
        qa_status TEXT DEFAULT 'pending',
        raw_output_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fight_id) REFERENCES fights(id),
        FOREIGN KEY (source_id) REFERENCES sources(id)
    )
    ''')

    # Fighter profiles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fighter_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fighter_name TEXT NOT NULL UNIQUE,
        total_mentions INTEGER DEFAULT 0,
        traits TEXT,
        styles TEXT,
        strengths TEXT,
        weaknesses TEXT,
        dfs_notes TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Cost tracking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        model TEXT NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cost_usd REAL,
        operation TEXT
    )
    ''')

    conn.commit()
    conn.close()

    log(f"Database initialized at {db_path}")
    print(f"✅ Database created: {db_path}")

if __name__ == "__main__":
    init_database()
