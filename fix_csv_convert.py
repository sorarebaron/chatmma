#!/usr/bin/env python3
"""
Proper CSV to DB converter that handles commas in fields.
Saves to data/chatmma.db
"""
import sqlite3
import csv
from pathlib import Path

# Paths
csv_path = Path.home() / "Desktop" / "ChatMMAPredictions.csv"
db_path = Path("data") / "chatmma.db"

# Make sure data directory exists
db_path.parent.mkdir(exist_ok=True)

print(f"Looking for CSV: {csv_path}")
if not csv_path.exists():
    print(f"❌ CSV not found!")
    exit(1)

# Delete old database
if db_path.exists():
    db_path.unlink()
    print("🗑️  Deleted old database")

# Create database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create full schema
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

# Read and clean CSV
print("📄 Reading CSV...")
with open(csv_path, 'rb') as f:
    raw_data = f.read()
    # Remove null bytes
    cleaned_data = raw_data.replace(b'\x00', b'')

# Decode
text = cleaned_data.decode('utf-8-sig', errors='ignore')

# Write to temp file
temp_csv = Path("temp_cleaned.csv")
temp_csv.write_text(text)

# Parse with csv module (handles commas in fields properly)
count = 0
with open(temp_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    print(f"📋 CSV columns: {reader.fieldnames}")

    for i, row in enumerate(reader, start=2):
        try:
            # Validate row has required fields
            if not all(k in row for k in ['date', 'analyst', 'event', 'location', 'fight', 'pick']):
                print(f"Line {i}: Missing required fields, skipping")
                continue

            # Event
            cursor.execute("INSERT OR IGNORE INTO events (name, date, location) VALUES (?, ?, ?)",
                          (row['event'], row['date'], row['location']))
            cursor.execute("SELECT id FROM events WHERE name = ?", (row['event'],))
            event_id = cursor.fetchone()[0]

            # Fight
            fight_str = row['fight'].strip()
            if ' vs ' not in fight_str:
                print(f"Line {i}: Invalid fight format '{fight_str}', skipping")
                continue

            parts = fight_str.split(' vs ', 1)
            fighter_a, fighter_b = parts[0].strip(), parts[1].strip()

            weight_class = row.get('weight class', '').strip()

            cursor.execute("INSERT OR IGNORE INTO fights (event_id, fighter_a, fighter_b, weight_class, scheduled_rounds) VALUES (?, ?, ?, ?, 3)",
                          (event_id, fighter_a, fighter_b, weight_class))
            cursor.execute("SELECT id FROM fights WHERE event_id = ? AND fighter_a = ? AND fighter_b = ?",
                          (event_id, fighter_a, fighter_b))
            result = cursor.fetchone()
            if not result:
                print(f"Line {i}: Could not create fight, skipping")
                continue
            fight_id = result[0]

            # Analyst
            analyst_name = row['analyst'].strip()
            platform = row.get('platform', '').strip()

            cursor.execute("INSERT OR IGNORE INTO analysts (name, real_name, type, publication) VALUES (?, ?, ?, ?)",
                          (analyst_name, analyst_name, 'article', platform))
            cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
            analyst_id = cursor.fetchone()[0]

            # Pick - check both directions (pick in fighter name OR fighter name in pick)
            pick_name = row['pick'].strip()

            if fighter_a.lower() in pick_name.lower() or pick_name.lower() in fighter_a.lower():
                pick = 'fighter_a'
            elif fighter_b.lower() in pick_name.lower() or pick_name.lower() in fighter_b.lower():
                pick = 'fighter_b'
            else:
                print(f"Line {i}: Cannot match pick '{pick_name}' to {fighter_a} vs {fighter_b}, skipping")
                continue

            # Context
            context = row.get('context', '').strip()

            # Insert prediction
            cursor.execute("INSERT INTO predictions (fight_id, analyst_id, pick, notes, qa_status) VALUES (?, ?, ?, ?, 'approved')",
                          (fight_id, analyst_id, pick, context))

            count += 1
            print(f"✓ {analyst_name}: {pick_name} for {fighter_a} vs {fighter_b}")

        except Exception as e:
            print(f"⚠️  Line {i}: Error - {e}")
            continue

# Clean up
temp_csv.unlink()

conn.commit()
conn.close()

print(f"\n✅ SUCCESS! Created {count} predictions")
print(f"📁 Database: {db_path.absolute()}")
print("\n📤 Next step: Upload data/chatmma.db to GitHub")
