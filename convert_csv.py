#!/usr/bin/env python3
"""
Simple CSV to DB converter that handles encoding issues.
Reads ChatMMAPredictions.csv from Desktop and creates data/chatmma.db
"""
import sqlite3
import os
from pathlib import Path

# Delete old database
db_path = Path("data/chatmma.db")
if db_path.exists():
    os.remove(db_path)
    print("🗑️  Deleted old database")

# Create fresh database with schema
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    date DATE NOT NULL,
    location TEXT,
    results_entered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    fighter_a TEXT NOT NULL,
    fighter_b TEXT NOT NULL,
    weight_class TEXT,
    is_main_card BOOLEAN DEFAULT 0,
    scheduled_rounds INTEGER DEFAULT 3,
    result TEXT,
    method TEXT,
    round INTEGER,
    time TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE analysts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    real_name TEXT,
    type TEXT NOT NULL,
    publication TEXT,
    url TEXT,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fight_id INTEGER NOT NULL,
    analyst_id INTEGER NOT NULL,
    pick TEXT NOT NULL,
    confidence TEXT,
    method TEXT,
    context_tags TEXT,
    notes TEXT,
    extraction_confidence REAL DEFAULT 100.0,
    qa_status TEXT DEFAULT 'approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES fights(id) ON DELETE CASCADE,
    FOREIGN KEY (analyst_id) REFERENCES analysts(id) ON DELETE CASCADE
);

CREATE TABLE fight_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fight_id INTEGER NOT NULL UNIQUE,
    total_predictions INTEGER DEFAULT 0,
    fighter_a_picks INTEGER DEFAULT 0,
    fighter_b_picks INTEGER DEFAULT 0,
    top_tags_fighter_a TEXT,
    top_tags_fighter_b TEXT,
    consensus_summary TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES fights(id) ON DELETE CASCADE
);

CREATE TABLE event_accuracy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analyst_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    total_picks INTEGER DEFAULT 0,
    correct_picks INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    FOREIGN KEY (analyst_id) REFERENCES analysts(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    UNIQUE(analyst_id, event_id)
);

CREATE TABLE context_tag_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL UNIQUE,
    category TEXT,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()
print("✅ Database schema created")

# Find CSV on Desktop
csv_path = Path.home() / "Desktop" / "ChatMMAPredictions.csv"
if not csv_path.exists():
    print(f"❌ CSV not found at: {csv_path}")
    exit(1)

print(f"📄 Reading CSV from: {csv_path}")

# Read CSV as binary and clean null bytes
with open(csv_path, 'rb') as f:
    raw_data = f.read()
    # Remove null bytes
    cleaned_data = raw_data.replace(b'\x00', b'')
    # Decode to text
    text_data = cleaned_data.decode('utf-8-sig', errors='ignore')

# Parse CSV manually (line by line)
lines = text_data.strip().split('\n')
if len(lines) < 2:
    print("❌ CSV appears empty")
    exit(1)

# Get headers
headers = [h.strip() for h in lines[0].split(',')]
print(f"📋 CSV columns: {headers}")

# Process each data row
prediction_count = 0
for i, line in enumerate(lines[1:], start=2):
    if not line.strip():
        continue

    # Split by comma (simple parser)
    values = [v.strip() for v in line.split(',')]

    if len(values) != len(headers):
        print(f"⚠️  Line {i}: column count mismatch, skipping")
        continue

    # Create row dict
    row = dict(zip(headers, values))

    try:
        # Get or create event
        cursor.execute("INSERT OR IGNORE INTO events (name, date, location) VALUES (?, ?, ?)",
                      (row['event'], row['date'], row['location']))
        cursor.execute("SELECT id FROM events WHERE name = ?", (row['event'],))
        event_id = cursor.fetchone()[0]

        # Parse fight
        fight_str = row['fight']
        if ' vs ' in fight_str:
            fighters = [f.strip() for f in fight_str.split(' vs ')]
            fighter_a, fighter_b = fighters[0], fighters[1]
        else:
            print(f"⚠️  Line {i}: Invalid fight format '{fight_str}', skipping")
            continue

        # Get or create fight
        cursor.execute("INSERT OR IGNORE INTO fights (event_id, fighter_a, fighter_b, weight_class, scheduled_rounds) VALUES (?, ?, ?, ?, 3)",
                      (event_id, fighter_a, fighter_b, row.get('weight class', '')))
        cursor.execute("SELECT id FROM fights WHERE event_id = ? AND fighter_a = ? AND fighter_b = ?",
                      (event_id, fighter_a, fighter_b))
        result = cursor.fetchone()
        if not result:
            print(f"⚠️  Line {i}: Could not find/create fight, skipping")
            continue
        fight_id = result[0]

        # Get or create analyst
        analyst_name = row['analyst']
        cursor.execute("INSERT OR IGNORE INTO analysts (name, real_name, type, publication) VALUES (?, ?, ?, ?)",
                      (analyst_name, analyst_name, 'article', row.get('platform', '')))
        cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
        analyst_id = cursor.fetchone()[0]

        # Determine pick
        pick_name = row['pick'].strip()
        if fighter_a.lower() in pick_name.lower() or pick_name.lower() in fighter_a.lower():
            pick = 'fighter_a'
        elif fighter_b.lower() in pick_name.lower() or pick_name.lower() in fighter_b.lower():
            pick = 'fighter_b'
        else:
            print(f"⚠️  Line {i}: Cannot match pick '{pick_name}' to fighters, skipping")
            continue

        # Insert prediction
        cursor.execute("INSERT INTO predictions (fight_id, analyst_id, pick, notes, qa_status) VALUES (?, ?, ?, ?, 'approved')",
                      (fight_id, analyst_id, pick, row.get('context', '')))
        prediction_count += 1
        print(f"✓ {analyst_name}: {pick_name} for {fighter_a} vs {fighter_b}")

    except Exception as e:
        print(f"⚠️  Line {i}: Error - {e}")
        continue

conn.commit()
conn.close()

print(f"\n✅ Done! Loaded {prediction_count} predictions")
print(f"📁 Database saved to: {db_path}")
print("\n📤 Next step: Upload data/chatmma.db to GitHub")
