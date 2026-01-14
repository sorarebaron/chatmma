import sqlite3
import csv

conn = sqlite3.connect("chatmma.db")
cursor = conn.cursor()

with open("ChatMMAPredictions.csv") as f:
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
        cursor.execute("INSERT INTO predictions (fight_id, analyst_id, pick, notes, qa_status) VALUES (?, ?, ?, ?, 'approved')",
                      (fight_id, analyst_id, pick, row['context']))
        print(f"✓ {analyst_name}: {pick_name} for {fighter_a} vs {fighter_b}")

conn.commit()
conn.close()
print("\nAll data loaded!")
