#!/usr/bin/env python3
"""
Load predictions from CSV file into chatmma.db.
Handles UFC 324 predictions with proper error checking.
"""
import csv
import sqlite3
import sys
from pathlib import Path

def load_csv_to_db(csv_file, db_file="data/chatmma.db"):
    """Load CSV predictions into database."""

    # Connect to database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Read CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Track stats
        added_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            try:
                # Extract fields
                analyst_name = row.get('analyst', '').strip()
                event_name = row.get('event', '').strip()
                fight_name = row.get('fight', '').strip()
                pick_name = row.get('pick', '').strip()
                context = row.get('context', '').strip()

                if not all([analyst_name, event_name, fight_name, pick_name]):
                    skipped_count += 1
                    errors.append(f"Row {row_num}: Missing required fields")
                    continue

                # Parse fighter names
                if ' vs ' in fight_name:
                    fighters = fight_name.split(' vs ')
                elif ' vs. ' in fight_name:
                    fighters = fight_name.split(' vs. ')
                else:
                    skipped_count += 1
                    errors.append(f"Row {row_num}: Can't parse fight '{fight_name}' - no 'vs' found")
                    continue

                if len(fighters) != 2:
                    skipped_count += 1
                    errors.append(f"Row {row_num}: Fight '{fight_name}' doesn't have exactly 2 fighters")
                    continue

                fighter_a = fighters[0].strip()
                fighter_b = fighters[1].strip()

                # Get or create event
                cursor.execute("SELECT id FROM events WHERE name = ?", (event_name,))
                event_result = cursor.fetchone()

                if not event_result:
                    # Create event
                    cursor.execute("""
                        INSERT INTO events (name, date, location, results_entered)
                        VALUES (?, ?, ?, ?)
                    """, (event_name, '2025-02-15', 'Las Vegas, Nevada', 0))
                    event_id = cursor.lastrowid
                else:
                    event_id = event_result[0]

                # Get or create fight
                cursor.execute("""
                    SELECT id FROM fights
                    WHERE event_id = ?
                    AND (
                        (fighter_a = ? AND fighter_b = ?)
                        OR (fighter_a = ? AND fighter_b = ?)
                    )
                """, (event_id, fighter_a, fighter_b, fighter_b, fighter_a))

                fight_result = cursor.fetchone()

                if not fight_result:
                    # Create fight
                    cursor.execute("""
                        INSERT INTO fights (event_id, fighter_a, fighter_b, weight_class)
                        VALUES (?, ?, ?, ?)
                    """, (event_id, fighter_a, fighter_b, row.get('weight_class', '')))
                    fight_id = cursor.lastrowid
                else:
                    fight_id = fight_result[0]

                # Get or create analyst
                cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
                analyst_result = cursor.fetchone()

                if not analyst_result:
                    # Create analyst
                    cursor.execute("""
                        INSERT INTO analysts (name, platform, total_predictions, accuracy_rate)
                        VALUES (?, ?, ?, ?)
                    """, (analyst_name, row.get('platform', ''), 0, None))
                    analyst_id = cursor.lastrowid
                else:
                    analyst_id = analyst_result[0]

                # Determine pick (fighter_a or fighter_b)
                if pick_name.lower() == fighter_a.lower():
                    pick = 'fighter_a'
                elif pick_name.lower() == fighter_b.lower():
                    pick = 'fighter_b'
                else:
                    # Try partial match
                    if pick_name.lower() in fighter_a.lower():
                        pick = 'fighter_a'
                    elif pick_name.lower() in fighter_b.lower():
                        pick = 'fighter_b'
                    else:
                        skipped_count += 1
                        errors.append(f"Row {row_num}: Can't match pick '{pick_name}' to fighters '{fighter_a}' or '{fighter_b}'")
                        continue

                # Check if prediction already exists
                cursor.execute("""
                    SELECT id FROM predictions
                    WHERE fight_id = ? AND analyst_id = ?
                """, (fight_id, analyst_id))

                if cursor.fetchone():
                    skipped_count += 1
                    errors.append(f"Row {row_num}: Duplicate prediction for {analyst_name} on {fight_name}")
                    continue

                # Insert prediction
                cursor.execute("""
                    INSERT INTO predictions (
                        fight_id, analyst_id, pick, confidence, method,
                        context_tags, notes, extraction_confidence, qa_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fight_id,
                    analyst_id,
                    pick,
                    None,  # confidence
                    None,  # method
                    None,  # context_tags
                    context,  # notes
                    1.0,  # extraction_confidence
                    'approved'  # qa_status
                ))

                added_count += 1
                print(f"Added: {analyst_name} picks {pick_name}")

            except Exception as e:
                skipped_count += 1
                errors.append(f"Row {row_num}: Error - {str(e)}")
                continue

        # Commit all changes
        conn.commit()
        conn.close()

        # Print summary
        print("\n" + "=" * 70)
        print(f"✅ Successfully added {added_count} predictions")
        print(f"⚠️  Skipped {skipped_count} rows")

        if errors:
            print(f"\n❌ Errors:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   {error}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_csv_to_db.py <csv_file>")
        print("Example: python load_csv_to_db.py predictions.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not Path(csv_file).exists():
        print(f"❌ Error: File '{csv_file}' not found")
        sys.exit(1)

    load_csv_to_db(csv_file)
