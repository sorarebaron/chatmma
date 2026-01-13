#!/usr/bin/env python3
"""
Manually add a prediction to the database (for testing or manual entry).

Usage:
    python scripts/add_prediction_manual.py \
      --event "UFC 323" \
      --fight "Manel Kape vs Brandon Royval" \
      --analyst "Analyst_001" \
      --pick "Manel Kape" \
      --confidence "high" \
      --method "DEC" \
      --tags "kape_wrestling_advantage,kape_sub_defense,royval_off_back" \
      --notes "Analyst believes Kape's wrestling will neutralize Royval's grappling."
"""
import sqlite3
import json
import argparse


def add_prediction(event_name, fight_str, analyst_name, pick, confidence, method, tags, notes):
    """Add prediction to database."""
    conn = sqlite3.connect("data/chatmma.db")
    cursor = conn.cursor()

    # Parse fight string
    fighters = [f.strip() for f in fight_str.split(" vs ")]
    if len(fighters) != 2:
        print(f"❌ Invalid fight format. Use 'Fighter A vs Fighter B'")
        return False

    fighter_a, fighter_b = fighters

    # Get event_id
    cursor.execute("SELECT id FROM events WHERE name = ?", (event_name,))
    event = cursor.fetchone()
    if not event:
        print(f"❌ Event not found: {event_name}")
        conn.close()
        return False

    event_id = event[0]

    # Get fight_id
    cursor.execute("""
        SELECT id, fighter_a, fighter_b FROM fights
        WHERE event_id = ?
        AND ((fighter_a LIKE ? AND fighter_b LIKE ?)
             OR (fighter_a LIKE ? AND fighter_b LIKE ?))
    """, (event_id, f"%{fighter_a}%", f"%{fighter_b}%",
          f"%{fighter_b}%", f"%{fighter_a}%"))

    fight = cursor.fetchone()
    if not fight:
        print(f"❌ Fight not found: {fighter_a} vs {fighter_b}")
        conn.close()
        return False

    fight_id, db_fighter_a, db_fighter_b = fight

    # Get or create analyst
    cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
    analyst = cursor.fetchone()

    if not analyst:
        cursor.execute("""
            INSERT INTO analysts (name, type, publication)
            VALUES (?, 'manual', 'Manual Entry')
        """, (analyst_name,))
        analyst_id = cursor.lastrowid
    else:
        analyst_id = analyst[0]

    # Determine pick (fighter_a or fighter_b)
    if pick.lower() in db_fighter_a.lower():
        pick_value = "fighter_a"
    elif pick.lower() in db_fighter_b.lower():
        pick_value = "fighter_b"
    else:
        print(f"❌ Pick '{pick}' doesn't match fighters: {db_fighter_a} or {db_fighter_b}")
        conn.close()
        return False

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Insert prediction
    cursor.execute("""
        INSERT INTO predictions (
            fight_id, analyst_id, pick, confidence, method,
            context_tags, notes, extraction_confidence, qa_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fight_id,
        analyst_id,
        pick_value,
        confidence,
        method,
        json.dumps(tag_list),
        notes,
        100,  # Manual entry is 100% confident
        'approved'
    ))

    conn.commit()
    conn.close()

    print(f"✅ Added prediction:")
    print(f"   Fight: {db_fighter_a} vs {db_fighter_b}")
    print(f"   Analyst: {analyst_name}")
    print(f"   Pick: {pick} ({confidence} confidence)")
    print(f"   Tags: {', '.join(tag_list)}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Manually add a prediction")
    parser.add_argument("--event", required=True, help="Event name")
    parser.add_argument("--fight", required=True, help="Fight (format: 'Fighter A vs Fighter B')")
    parser.add_argument("--analyst", required=True, help="Analyst name")
    parser.add_argument("--pick", required=True, help="Fighter picked to win")
    parser.add_argument("--confidence", choices=["high", "medium", "low"], default="medium")
    parser.add_argument("--method", choices=["KO", "SUB", "DEC", "FINISH"], help="Expected method")
    parser.add_argument("--tags", help="Comma-separated context tags")
    parser.add_argument("--notes", required=True, help="Reasoning notes")

    args = parser.parse_args()

    add_prediction(
        args.event,
        args.fight,
        args.analyst,
        args.pick,
        args.confidence,
        args.method,
        args.tags,
        args.notes
    )


if __name__ == "__main__":
    main()
