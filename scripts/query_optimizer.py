#!/usr/bin/env python3
"""
Query optimizer for cost-efficient database filtering.
Filters predictions before sending to Claude to minimize token usage.
"""
import sqlite3
import json
from collections import Counter
from datetime import datetime


class QueryOptimizer:
    """Optimizes database queries for cost-efficient chatbot responses."""

    def __init__(self, db_path="data/chatmma.db"):
        self.db_path = db_path

    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def get_fight_by_fighters(self, fighter_name_a, fighter_name_b, event_name=None):
        """
        Find fight by fighter names (fuzzy match).
        Returns fight_id, fighter names, and event info.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if event_name:
            query = """
                SELECT f.id, f.fighter_a, f.fighter_b, e.name, e.date, e.results_entered
                FROM fights f
                JOIN events e ON f.event_id = e.id
                WHERE e.name = ?
                AND (
                    (f.fighter_a LIKE ? OR f.fighter_b LIKE ?)
                    OR (f.fighter_a LIKE ? OR f.fighter_b LIKE ?)
                )
            """
            params = (event_name, f"%{fighter_name_a}%", f"%{fighter_name_a}%",
                      f"%{fighter_name_b}%", f"%{fighter_name_b}%")
        else:
            # Get most recent event with these fighters
            query = """
                SELECT f.id, f.fighter_a, f.fighter_b, e.name, e.date, e.results_entered
                FROM fights f
                JOIN events e ON f.event_id = e.id
                WHERE (
                    (f.fighter_a LIKE ? OR f.fighter_b LIKE ?)
                    OR (f.fighter_a LIKE ? OR f.fighter_b LIKE ?)
                )
                ORDER BY e.date DESC
                LIMIT 1
            """
            params = (f"%{fighter_name_a}%", f"%{fighter_name_a}%",
                      f"%{fighter_name_b}%", f"%{fighter_name_b}%")

        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "fight_id": result[0],
                "fighter_a": result[1],
                "fighter_b": result[2],
                "event": result[3],
                "date": result[4],
                "results_entered": bool(result[5])
            }
        return None

    def get_fight_predictions(self, fight_id, min_confidence=None):
        """
        Get all predictions for a fight with context tags and notes.
        Returns structured data optimized for prompt generation.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                p.pick,
                p.confidence,
                p.method,
                p.context_tags,
                p.notes,
                a.name,
                a.real_name,
                a.accuracy_rate,
                a.total_predictions
            FROM predictions p
            JOIN analysts a ON p.analyst_id = a.id
            WHERE p.fight_id = ?
            AND p.qa_status = 'approved'
        """
        params = [fight_id]

        if min_confidence:
            query += " AND p.confidence = ?"
            params.append(min_confidence)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        predictions = []
        for row in rows:
            predictions.append({
                "pick": row[0],
                "confidence": row[1],
                "method": row[2],
                "context_tags": json.loads(row[3]) if row[3] else [],
                "notes": row[4],
                "analyst_name": row[5],
                "analyst_real_name": row[6],
                "analyst_accuracy": row[7],
                "analyst_total_predictions": row[8]
            })

        return predictions

    def aggregate_fight_context(self, fight_id, reveal_names=False):
        """
        Aggregate predictions into optimized context for Claude.
        This is the KEY function for cost optimization.

        Returns:
        - Pick distribution
        - Top context tags
        - Example rationales
        - Analyst accuracy tiers (if reveal_names=True)
        """
        predictions = self.get_fight_predictions(fight_id)

        if not predictions:
            return None

        # Get fight details
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fighter_a, fighter_b, e.name, e.results_entered
            FROM fights f
            JOIN events e ON f.event_id = e.id
            WHERE f.id = ?
        """, (fight_id,))
        fight_data = cursor.fetchone()
        conn.close()

        if not fight_data:
            return None

        fighter_a, fighter_b, event_name, results_entered = fight_data

        # Aggregate picks
        picks_a = [p for p in predictions if p["pick"] == "fighter_a"]
        picks_b = [p for p in predictions if p["pick"] == "fighter_b"]

        # Aggregate context tags
        tags_a = []
        tags_b = []
        for p in picks_a:
            tags_a.extend(p["context_tags"])
        for p in picks_b:
            tags_b.extend(p["context_tags"])

        tag_counts_a = Counter(tags_a)
        tag_counts_b = Counter(tags_b)

        # Aggregate methods
        methods_a = Counter([p["method"] for p in picks_a if p["method"]])
        methods_b = Counter([p["method"] for p in picks_b if p["method"]])

        # Get top analysts by accuracy
        picks_a_sorted = sorted(picks_a, key=lambda x: x["analyst_accuracy"] or 0, reverse=True)
        picks_b_sorted = sorted(picks_b, key=lambda x: x["analyst_accuracy"] or 0, reverse=True)

        # Get example rationales (top 2-3 from high-accuracy analysts)
        example_notes_a = [p["notes"] for p in picks_a_sorted[:3] if p["notes"]]
        example_notes_b = [p["notes"] for p in picks_b_sorted[:3] if p["notes"]]

        context = {
            "fight": {
                "fighter_a": fighter_a,
                "fighter_b": fighter_b,
                "event": event_name,
                "results_entered": bool(results_entered)
            },
            "summary": {
                "total_predictions": len(predictions),
                "picks_for_a": len(picks_a),
                "picks_for_b": len(picks_b)
            },
            "fighter_a_context": {
                "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counts_a.most_common(5)],
                "methods": dict(methods_a),
                "example_rationales": example_notes_a
            },
            "fighter_b_context": {
                "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counts_b.most_common(5)],
                "methods": dict(methods_b),
                "example_rationales": example_notes_b
            }
        }

        # Add analyst accuracy tiers
        if reveal_names or results_entered:
            # Show analyst names after event
            high_accuracy_a = [p for p in picks_a if (p["analyst_accuracy"] or 0) >= 60]
            high_accuracy_b = [p for p in picks_b if (p["analyst_accuracy"] or 0) >= 60]

            context["analyst_info"] = {
                "fighter_a_high_accuracy_count": len(high_accuracy_a),
                "fighter_b_high_accuracy_count": len(high_accuracy_b),
                "reveal_names": reveal_names,
                "top_analysts_a": [p["analyst_real_name"] or p["analyst_name"] for p in picks_a_sorted[:5]],
                "top_analysts_b": [p["analyst_real_name"] or p["analyst_name"] for p in picks_b_sorted[:5]]
            }
        else:
            # Don't reveal names before event
            high_accuracy_a = [p for p in picks_a if (p["analyst_accuracy"] or 0) >= 60]
            high_accuracy_b = [p for p in picks_b if (p["analyst_accuracy"] or 0) >= 60]

            context["analyst_info"] = {
                "fighter_a_high_accuracy_count": len(high_accuracy_a),
                "fighter_b_high_accuracy_count": len(high_accuracy_b),
                "reveal_names": False
            }

        return context

    def get_all_events(self):
        """Get all events from database, ordered by date (most recent first)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, date, location, results_entered
            FROM events
            ORDER BY date DESC
        """)

        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'name': row[1],
                'date': row[2],
                'location': row[3],
                'results_entered': row[4]
            })

        conn.close()
        return events

    def get_full_event_context(self, event_name=None):
        """
        Get complete context for an event (or most recent event).
        Returns all fights with aggregated predictions - optimized for small events.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get event
        if event_name:
            cursor.execute("""
                SELECT id, name, date, location
                FROM events
                WHERE name = ?
            """, (event_name,))
        else:
            cursor.execute("""
                SELECT id, name, date, location
                FROM events
                ORDER BY date DESC
                LIMIT 1
            """)

        event_row = cursor.fetchone()
        if not event_row:
            conn.close()
            return None

        event_id, event_name, event_date, event_location = event_row

        # Get all fights for this event with predictions
        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b, f.weight_class
            FROM fights f
            WHERE f.event_id = ?
            ORDER BY f.id
        """, (event_id,))

        fights = []
        for fight_row in cursor.fetchall():
            fight_id, fighter_a, fighter_b, weight_class = fight_row

            # Get predictions for this fight
            cursor.execute("""
                SELECT
                    p.pick,
                    p.notes,
                    a.name
                FROM predictions p
                JOIN analysts a ON p.analyst_id = a.id
                WHERE p.fight_id = ?
                AND p.qa_status = 'approved'
            """, (fight_id,))

            predictions = []
            picks_a = 0
            picks_b = 0

            for pred_row in cursor.fetchall():
                pick, notes, analyst_name = pred_row
                predictions.append({
                    'pick': pick,
                    'notes': notes,
                    'analyst': analyst_name
                })

                if pick == 'fighter_a':
                    picks_a += 1
                elif pick == 'fighter_b':
                    picks_b += 1

            fights.append({
                'fight_id': fight_id,
                'fighter_a': fighter_a,
                'fighter_b': fighter_b,
                'weight_class': weight_class,
                'picks_for_a': picks_a,
                'picks_for_b': picks_b,
                'total_picks': picks_a + picks_b,
                'predictions': predictions
            })

        conn.close()

        return {
            'event_name': event_name,
            'event_date': event_date,
            'event_location': event_location,
            'fights': fights
        }

    def get_lightweight_context(self):
        """
        Get minimal context about available data (for fallback queries).
        Returns just event names and fight matchups - very token efficient.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.name, e.date, f.fighter_a, f.fighter_b
            FROM events e
            JOIN fights f ON f.event_id = e.id
            ORDER BY e.date DESC, f.id
        """)

        data = {}
        for row in cursor.fetchall():
            event_name = row[0]
            if event_name not in data:
                data[event_name] = {
                    'date': row[1],
                    'fights': []
                }
            data[event_name]['fights'].append(f"{row[2]} vs {row[3]}")

        conn.close()
        return data

    def get_event_predictions_summary(self, event_name):
        """Get summary of all predictions for an event."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.id, e.name, e.date, e.results_entered
            FROM events e
            WHERE e.name = ?
        """, (event_name,))

        event_data = cursor.fetchone()
        if not event_data:
            conn.close()
            return None

        event_id = event_data[0]

        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b
            FROM fights f
            WHERE f.event_id = ?
        """, (event_id,))

        fights = cursor.fetchall()
        conn.close()

        summaries = []
        for fight in fights:
            fight_id, fighter_a, fighter_b = fight
            context = self.aggregate_fight_context(fight_id, reveal_names=event_data[3])
            if context:
                summaries.append(context)

        return {
            "event": event_name,
            "date": event_data[2],
            "results_entered": bool(event_data[3]),
            "fight_summaries": summaries
        }


# Example usage
if __name__ == "__main__":
    optimizer = QueryOptimizer()

    # Test: Get fight context
    fight = optimizer.get_fight_by_fighters("Kape", "Royval")
    if fight:
        print(f"Found fight: {fight}")
        context = optimizer.aggregate_fight_context(fight["fight_id"])
        print(json.dumps(context, indent=2))
