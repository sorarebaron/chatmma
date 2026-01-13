#!/usr/bin/env python3
"""
Load extracted predictions into database.
Usage: python scripts/load_predictions.py --event "UFC 323"
"""
import os
import json
import sqlite3
import argparse
from pathlib import Path


class PredictionLoader:
    """Loads predictions into database."""

    def __init__(self, db_path="data/chatmma.db"):
        self.db_path = db_path

    def load_event_from_yaml(self, yaml_path, event_name):
        """Load event and fights from YAML."""
        import yaml
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        for event in data.get('events', []):
            if event['name'] == event_name:
                return event

        return None

    def ensure_event_exists(self, event_data):
        """Ensure event exists in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO events (name, date, location, results_entered)
            VALUES (?, ?, ?, ?)
        """, (
            event_data['name'],
            event_data['date'],
            event_data.get('location', ''),
            0
        ))

        cursor.execute("SELECT id FROM events WHERE name = ?", (event_data['name'],))
        event_id = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        return event_id

    def ensure_fights_exist(self, event_id, fights):
        """Ensure fights exist in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fight_ids = {}

        for fight in fights:
            cursor.execute("""
                INSERT OR IGNORE INTO fights (
                    event_id, fighter_a, fighter_b, weight_class,
                    is_main_card, scheduled_rounds
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                fight['fighter_a'],
                fight['fighter_b'],
                fight.get('weight_class', ''),
                fight.get('is_main_card', False),
                fight.get('scheduled_rounds', 3)
            ))

            cursor.execute("""
                SELECT id FROM fights
                WHERE event_id = ?
                AND fighter_a = ?
                AND fighter_b = ?
            """, (event_id, fight['fighter_a'], fight['fighter_b']))

            fight_id = cursor.fetchone()[0]
            fight_key = f"{fight['fighter_a']}_{fight['fighter_b']}"
            fight_ids[fight_key] = fight_id

        conn.commit()
        conn.close()

        return fight_ids

    def ensure_analyst_exists(self, analyst_name, analyst_type="article", publication=""):
        """Ensure analyst exists in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO analysts (name, type, publication)
            VALUES (?, ?, ?)
        """, (analyst_name, analyst_type, publication))

        cursor.execute("SELECT id FROM analysts WHERE name = ?", (analyst_name,))
        analyst_id = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        return analyst_id

    def load_predictions(self, extraction_file, analyst_name, fight_ids):
        """
        Load predictions from extraction JSON into database.

        Args:
            extraction_file: Path to extraction JSON
            analyst_name: Analyst identifier (e.g., "Analyst_001")
            fight_ids: Dict mapping "FighterA_FighterB" to fight_id
        """
        with open(extraction_file, 'r') as f:
            data = json.load(f)

        predictions = data if isinstance(data, list) else data.get('predictions', [])

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        loaded_count = 0

        for pred in predictions:
            # Find fight_id
            fight_key_1 = f"{pred['fighter_a']}_{pred['fighter_b']}"
            fight_key_2 = f"{pred['fighter_b']}_{pred['fighter_a']}"

            fight_id = fight_ids.get(fight_key_1) or fight_ids.get(fight_key_2)

            if not fight_id:
                print(f"⚠️  Skipping: {pred['fighter_a']} vs {pred['fighter_b']} (fight not found)")
                continue

            # Determine pick (fighter_a or fighter_b)
            if pred['pick'] == pred['fighter_a']:
                pick = 'fighter_a'
            elif pred['pick'] == pred['fighter_b']:
                pick = 'fighter_b'
            else:
                print(f"⚠️  Skipping: Invalid pick {pred['pick']}")
                continue

            # Get analyst_id
            analyst_id = self.ensure_analyst_exists(analyst_name)

            # Insert prediction
            cursor.execute("""
                INSERT OR REPLACE INTO predictions (
                    fight_id, analyst_id, pick, confidence, method,
                    context_tags, notes, extraction_confidence, qa_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fight_id,
                analyst_id,
                pick,
                pred.get('confidence', 'medium'),
                pred.get('method'),
                json.dumps(pred.get('context_tags', [])),
                pred.get('notes', ''),
                pred.get('extraction_confidence', 90),
                'approved'
            ))

            loaded_count += 1

        conn.commit()
        conn.close()

        return loaded_count


def main():
    parser = argparse.ArgumentParser(description="Load predictions into database")
    parser.add_argument("--event", required=True, help="Event name")
    parser.add_argument("--fights", default="fights.yaml", help="Fights YAML")
    parser.add_argument("--extractions", default="data/extractions", help="Extractions directory")
    args = parser.parse_args()

    loader = PredictionLoader()

    # Load event data
    event_data = loader.load_event_from_yaml(args.fights, args.event)
    if not event_data:
        print(f"❌ Event {args.event} not found in {args.fights}")
        return

    print(f"✓ Loaded event: {args.event} ({event_data['date']})")

    # Ensure event exists in DB
    event_id = loader.ensure_event_exists(event_data)
    print(f"✓ Event ID: {event_id}")

    # Ensure fights exist in DB
    fight_ids = loader.ensure_fights_exist(event_id, event_data['fights'])
    print(f"✓ Loaded {len(fight_ids)} fights")

    # Load all extraction files for this event
    extractions_dir = Path(args.extractions)
    extraction_files = list(extractions_dir.glob(f"{args.event}_*.json"))

    if not extraction_files:
        print(f"⚠️  No extraction files found for {args.event}")
        return

    print(f"\n📥 Loading {len(extraction_files)} extraction files...")

    total_loaded = 0
    for extraction_file in extraction_files:
        # Extract analyst name from filename
        # Format: UFC_323_Analyst_001.json
        filename = extraction_file.stem
        parts = filename.split('_')

        if len(parts) >= 3:
            analyst_name = '_'.join(parts[2:])  # "Analyst_001"
        else:
            analyst_name = filename

        print(f"\n  Loading {analyst_name}...")
        count = loader.load_predictions(extraction_file, analyst_name, fight_ids)
        print(f"  ✓ Loaded {count} predictions")
        total_loaded += count

    print(f"\n✅ Total predictions loaded: {total_loaded}")


if __name__ == "__main__":
    main()
