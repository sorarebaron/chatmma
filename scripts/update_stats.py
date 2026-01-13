#!/usr/bin/env python3
"""
Update analyst accuracy stats and generate fight summaries.
Usage: python scripts/update_stats.py [--event "UFC 323"]
"""
import sqlite3
import json
import argparse
from collections import Counter


class StatsUpdater:
    """Updates statistics and generates summaries."""

    def __init__(self, db_path="data/chatmma.db"):
        self.db_path = db_path

    def update_analyst_accuracy(self, event_id=None):
        """
        Update analyst accuracy stats based on fight results.
        If event_id provided, update for that event only.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all analysts
        cursor.execute("SELECT id, name FROM analysts")
        analysts = cursor.fetchall()

        for analyst_id, analyst_name in analysts:
            # Get all predictions for this analyst
            if event_id:
                query = """
                    SELECT p.pick, f.result
                    FROM predictions p
                    JOIN fights f ON p.fight_id = f.id
                    WHERE p.analyst_id = ?
                    AND f.event_id = ?
                    AND f.result IS NOT NULL
                """
                cursor.execute(query, (analyst_id, event_id))
            else:
                query = """
                    SELECT p.pick, f.result
                    FROM predictions p
                    JOIN fights f ON p.fight_id = f.id
                    WHERE p.analyst_id = ?
                    AND f.result IS NOT NULL
                """
                cursor.execute(query, (analyst_id,))

            results = cursor.fetchall()

            if not results:
                continue

            total = len(results)
            correct = sum(1 for pick, result in results if pick == result)
            accuracy = (correct / total * 100) if total > 0 else 0

            # Update analyst record
            cursor.execute("""
                UPDATE analysts
                SET total_predictions = ?,
                    correct_predictions = ?,
                    accuracy_rate = ?
                WHERE id = ?
            """, (total, correct, accuracy, analyst_id))

            print(f"  {analyst_name}: {correct}/{total} ({accuracy:.1f}%)")

        conn.commit()
        conn.close()

    def generate_fight_summaries(self, event_id=None):
        """
        Generate pre-computed fight summaries for cost optimization.
        These summaries can be used for quick responses.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get fights to summarize
        if event_id:
            cursor.execute("""
                SELECT id, fighter_a, fighter_b, event_id
                FROM fights
                WHERE event_id = ?
            """, (event_id,))
        else:
            cursor.execute("""
                SELECT f.id, f.fighter_a, f.fighter_b, f.event_id
                FROM fights f
                JOIN events e ON f.event_id = e.id
                WHERE e.results_entered = 0
            """)

        fights = cursor.fetchall()

        for fight_id, fighter_a, fighter_b, event_id in fights:
            # Get all predictions for this fight
            cursor.execute("""
                SELECT pick, context_tags, method
                FROM predictions
                WHERE fight_id = ?
                AND qa_status = 'approved'
            """, (fight_id,))

            predictions = cursor.fetchall()

            if not predictions:
                continue

            # Count picks
            picks_a = sum(1 for p in predictions if p[0] == 'fighter_a')
            picks_b = sum(1 for p in predictions if p[0] == 'fighter_b')

            # Aggregate tags
            tags_a = []
            tags_b = []
            for pick, tags_json, method in predictions:
                tags = json.loads(tags_json) if tags_json else []
                if pick == 'fighter_a':
                    tags_a.extend(tags)
                else:
                    tags_b.extend(tags)

            top_tags_a = Counter(tags_a).most_common(5)
            top_tags_b = Counter(tags_b).most_common(5)

            # Generate consensus summary
            consensus = f"{fighter_a} favored by {picks_a} analysts, {fighter_b} by {picks_b}."

            if top_tags_a:
                top_tag = top_tags_a[0][0].replace('_', ' ')
                consensus += f" Key factor for {fighter_a}: {top_tag}."

            # Insert or update summary
            cursor.execute("""
                INSERT OR REPLACE INTO fight_summaries (
                    fight_id, total_predictions,
                    fighter_a_picks, fighter_b_picks,
                    top_tags_fighter_a, top_tags_fighter_b,
                    consensus_summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                fight_id,
                len(predictions),
                picks_a,
                picks_b,
                json.dumps([{"tag": t, "count": c} for t, c in top_tags_a]),
                json.dumps([{"tag": t, "count": c} for t, c in top_tags_b]),
                consensus
            ))

            print(f"  ✓ {fighter_a} vs {fighter_b}: {consensus}")

        conn.commit()
        conn.close()

    def calculate_event_accuracy(self, event_id):
        """Calculate per-analyst accuracy for a specific event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all analysts who made predictions for this event
        cursor.execute("""
            SELECT DISTINCT p.analyst_id, a.name
            FROM predictions p
            JOIN analysts a ON p.analyst_id = a.id
            JOIN fights f ON p.fight_id = f.id
            WHERE f.event_id = ?
        """, (event_id,))

        analysts = cursor.fetchall()

        for analyst_id, analyst_name in analysts:
            # Get predictions vs results for this event
            cursor.execute("""
                SELECT p.pick, f.result
                FROM predictions p
                JOIN fights f ON p.fight_id = f.id
                WHERE p.analyst_id = ?
                AND f.event_id = ?
                AND f.result IS NOT NULL
            """, (analyst_id, event_id))

            results = cursor.fetchall()

            if not results:
                continue

            total = len(results)
            correct = sum(1 for pick, result in results if pick == result)
            accuracy = (correct / total * 100) if total > 0 else 0

            # Insert into event_accuracy table
            cursor.execute("""
                INSERT OR REPLACE INTO event_accuracy (
                    analyst_id, event_id, total_picks, correct_picks, accuracy_rate
                )
                VALUES (?, ?, ?, ?, ?)
            """, (analyst_id, event_id, total, correct, accuracy))

            print(f"  {analyst_name}: {correct}/{total} ({accuracy:.1f}%)")

        conn.commit()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Update stats and generate summaries")
    parser.add_argument("--event", help="Event name to update")
    parser.add_argument("--action", choices=["accuracy", "summaries", "all"], default="all")
    args = parser.parse_args()

    updater = StatsUpdater()

    event_id = None
    if args.event:
        # Get event_id
        conn = sqlite3.connect(updater.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM events WHERE name = ?", (args.event,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            print(f"❌ Event not found: {args.event}")
            return

        event_id = result[0]
        print(f"✓ Event ID: {event_id}\n")

    if args.action in ["accuracy", "all"]:
        print("📊 Updating analyst accuracy...")
        updater.update_analyst_accuracy(event_id)

    if args.action in ["summaries", "all"]:
        print("\n📝 Generating fight summaries...")
        updater.generate_fight_summaries(event_id)

    print("\n✅ Stats updated successfully")


if __name__ == "__main__":
    main()
