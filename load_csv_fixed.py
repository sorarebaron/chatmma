import sqlite3
import csv
import os
from pathlib import Path

# First try to create empty database with schema
conn = sqlite3.connect("data/chatmma.db")
cursor = conn.cursor()

# Create schema if needed
cursor.executescript("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    date DATE NOT NULL,
    location TEXT,
    results_entered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fights (
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

CREATE TABLE IF NOT EXISTS analysts (
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

CREATE TABLE IF NOT EXISTS predictions (
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
""")
conn.commit()

# Look for CSV on Desktop
desktop_path = Path.home() / "Desktop" / "ChatMMAPredictions.csv"
if not desktop_path.exists():
    print(f"❌ CSV not found at: {desktop_path}")
    print("Please make sure ChatMMAPredictions.csv is on your Desktop")
    exit(1)

print(f"Loading CSV from: {desktop_path}")

with open(desktop_path, encoding='utf-8-sig', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Get event
        event = row['event']
        cursor.execute("INSERT OR IGNORE INTO events (name, date, location) VALUES (?, ?, ?)",
                      (event, row['date'], row['location']))
        cursor.execute("SELECT id FROM events WHERE name = ?", (event,))
        event_id = cursor.fetchone()[0]

        # Parse fighters from fight column
        fight_str = row['fight']
        if ' vs ' in fight_str:
            fighters = [f.strip() for f in fight_str.split(' vs ')]
        else:
            print(f"Warning: Invalid fight format: {fight_str}")
            continue

        fighter_a, fighter_b = fighters[0], fighters[1]

        # Create fight
        cursor.execute("INSERT OR IGNORE INTO fights (event_id, fighter_a, fighter_b, weight_class, scheduled_rounds) VALUES (?, ?, ?, ?, 3)",
                      (event_id, fighter_a, fighter_b, row['weight class']))
        cursor.execute("SELECT id FROM fights WHERE event_id = ? AND fighter_a = ? AND fighter_b = ?",
                      (event_id, fighter_a, fighter_b))
        result = cursor.fetchone()
        if result:
            fight_id = result[0]
        else:
            print(f"Warning: Could not find fight: {fighter_a} vs {fighter_b}")
            continue

        # Create analyst (use full name from 'analyst' column)
        analyst_name = row['analyst']
        cursor.execute("INSERT OR IGNORE INTO analysts (name, real_name, type, publication) VALUES (?, ?, ?, ?)",
                      (analyst_name, analyst_name, 'article', row['platform']))
        cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
        analyst_id = cursor.fetchone()[0]

        # Determine pick
        pick_name = row['pick'].strip()
        if fighter_a.lower() in pick_name.lower() or pick_name.lower() in fighter_a.lower():
            pick = 'fighter_a'
        elif fighter_b.lower() in pick_name.lower() or pick_name.lower() in fighter_b.lower():
            pick = 'fighter_b'
        else:
            print(f"Warning: Cannot match pick '{pick_name}' to {fighter_a} vs {fighter_b}")
            continue

        # Insert prediction
        try:
            cursor.execute("INSERT INTO predictions (fight_id, analyst_id, pick, notes, qa_status) VALUES (?, ?, ?, ?, 'approved')",
                          (fight_id, analyst_id, pick, row.get('context', '')))
            print(f"✓ {analyst_name}: {pick_name} for {fighter_a} vs {fighter_b}")
        except Exception as e:
            print(f"⚠️  Error adding prediction: {e}")
            continue

conn.commit()
conn.close()
print("\n✅ All data loaded!")
print(f"📁 Database saved to: data/chatmma.db")
print("\n📤 Next step: Upload data/chatmma.db to GitHub at the data/ folder")
