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
            # Match where BOTH fighters are in the fight (in either order)
            query = """
                SELECT f.id, f.fighter_a, f.fighter_b, e.name, e.date, e.results_entered
                FROM fights f
                JOIN events e ON f.event_id = e.id
                WHERE e.name = ?
                AND (
                    (f.fighter_a LIKE ? AND f.fighter_b LIKE ?)
                    OR (f.fighter_a LIKE ? AND f.fighter_b LIKE ?)
                )
            """
            params = (event_name,
                      f"%{fighter_name_a}%", f"%{fighter_name_b}%",
                      f"%{fighter_name_b}%", f"%{fighter_name_a}%")
        else:
            # Get most recent event with these fighters
            query = """
                SELECT f.id, f.fighter_a, f.fighter_b, e.name, e.date, e.results_entered
                FROM fights f
                JOIN events e ON f.event_id = e.id
                WHERE (
                    (f.fighter_a LIKE ? AND f.fighter_b LIKE ?)
                    OR (f.fighter_a LIKE ? AND f.fighter_b LIKE ?)
                )
                ORDER BY e.date DESC
                LIMIT 1
            """
            params = (f"%{fighter_name_a}%", f"%{fighter_name_b}%",
                      f"%{fighter_name_b}%", f"%{fighter_name_a}%")

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

    def get_inside_distance_picks(self, event_name):
        """
        Get fighters most likely to win inside the distance (KO/TKO/SUB).
        Returns list of fights where consensus expects finish.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get event ID
        cursor.execute("SELECT id FROM events WHERE name = ?", (event_name,))
        event_data = cursor.fetchone()
        if not event_data:
            conn.close()
            return None

        event_id = event_data[0]

        # Get all fights for this event
        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b
            FROM fights f
            WHERE f.event_id = ?
        """, (event_id,))

        fights = cursor.fetchall()

        inside_distance_fights = []

        for fight_id, fighter_a, fighter_b in fights:
            # Get predictions for this fight
            cursor.execute("""
                SELECT p.pick, p.method, a.name, a.real_name, a.accuracy_rate
                FROM predictions p
                JOIN analysts a ON p.analyst_id = a.id
                WHERE p.fight_id = ?
                AND p.qa_status = 'approved'
                AND p.method IN ('KO', 'TKO', 'SUB', 'Submission', 'Knockout')
            """, (fight_id,))

            finish_predictions = cursor.fetchall()

            if len(finish_predictions) >= 3:  # At least 3 analysts expect a finish
                # Aggregate by fighter
                finish_by_fighter = {'fighter_a': [], 'fighter_b': []}
                for pick, method, analyst_name, real_name, accuracy in finish_predictions:
                    if pick in finish_by_fighter:
                        finish_by_fighter[pick].append({
                            'method': method,
                            'analyst': real_name or analyst_name,
                            'accuracy': accuracy
                        })

                # Find which fighter has more finish predictions
                fighter_a_finishes = len(finish_by_fighter['fighter_a'])
                fighter_b_finishes = len(finish_by_fighter['fighter_b'])

                if fighter_a_finishes > 0 or fighter_b_finishes > 0:
                    favored_fighter = fighter_a if fighter_a_finishes >= fighter_b_finishes else fighter_b
                    finish_count = max(fighter_a_finishes, fighter_b_finishes)
                    methods = finish_by_fighter['fighter_a' if favored_fighter == fighter_a else 'fighter_b']

                    inside_distance_fights.append({
                        'fight': f"{fighter_a} vs {fighter_b}",
                        'fighter_a': fighter_a,
                        'fighter_b': fighter_b,
                        'favored_fighter': favored_fighter,
                        'finish_prediction_count': finish_count,
                        'methods': methods,
                        'total_finish_predictions': len(finish_predictions)
                    })

        conn.close()

        # Sort by finish prediction count
        inside_distance_fights.sort(key=lambda x: x['finish_prediction_count'], reverse=True)

        return {
            'event': event_name,
            'inside_distance_picks': inside_distance_fights
        }

    def get_event_consensus_picks(self, event_name):
        """
        Get consensus picks for all fights in an event.
        Returns fights sorted by consensus strength.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get event ID
        cursor.execute("SELECT id, results_entered FROM events WHERE name = ?", (event_name,))
        event_data = cursor.fetchone()
        if not event_data:
            conn.close()
            return None

        event_id, results_entered = event_data

        # Get all fights
        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b
            FROM fights f
            WHERE f.event_id = ?
        """, (event_id,))

        fights = cursor.fetchall()

        consensus_picks = []

        for fight_id, fighter_a, fighter_b in fights:
            # Get prediction counts
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN p.pick = 'fighter_a' THEN 1 ELSE 0 END) as picks_a,
                    SUM(CASE WHEN p.pick = 'fighter_b' THEN 1 ELSE 0 END) as picks_b,
                    COUNT(*) as total_picks
                FROM predictions p
                WHERE p.fight_id = ?
                AND p.qa_status = 'approved'
            """, (fight_id,))

            result = cursor.fetchone()
            picks_a, picks_b, total_picks = result if result else (0, 0, 0)

            if total_picks > 0:
                # Determine consensus
                consensus_fighter = fighter_a if picks_a > picks_b else fighter_b
                consensus_count = max(picks_a, picks_b)
                consensus_percentage = (consensus_count / total_picks) * 100

                # Get high accuracy analyst count for consensus pick
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM predictions p
                    JOIN analysts a ON p.analyst_id = a.id
                    WHERE p.fight_id = ?
                    AND p.pick = ?
                    AND a.accuracy_rate >= 60
                    AND p.qa_status = 'approved'
                """, (fight_id, 'fighter_a' if consensus_fighter == fighter_a else 'fighter_b'))

                high_accuracy_count = cursor.fetchone()[0]

                consensus_picks.append({
                    'fight': f"{fighter_a} vs {fighter_b}",
                    'fighter_a': fighter_a,
                    'fighter_b': fighter_b,
                    'consensus_fighter': consensus_fighter,
                    'consensus_count': consensus_count,
                    'opposing_count': min(picks_a, picks_b),
                    'total_predictions': total_picks,
                    'consensus_percentage': consensus_percentage,
                    'high_accuracy_count': high_accuracy_count
                })

        conn.close()

        # Sort by consensus strength
        consensus_picks.sort(key=lambda x: x['consensus_percentage'], reverse=True)

        return {
            'event': event_name,
            'results_entered': bool(results_entered),
            'consensus_picks': consensus_picks
        }

    def get_event_underdogs(self, event_name):
        """
        Get underdog picks for an event.
        Underdogs are fighters with minority analyst support but potential value.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get event ID
        cursor.execute("SELECT id, results_entered FROM events WHERE name = ?", (event_name,))
        event_data = cursor.fetchone()
        if not event_data:
            conn.close()
            return None

        event_id, results_entered = event_data

        # Get all fights
        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b
            FROM fights f
            WHERE f.event_id = ?
        """, (event_id,))

        fights = cursor.fetchall()

        underdog_picks = []

        for fight_id, fighter_a, fighter_b in fights:
            # Get prediction counts
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN p.pick = 'fighter_a' THEN 1 ELSE 0 END) as picks_a,
                    SUM(CASE WHEN p.pick = 'fighter_b' THEN 1 ELSE 0 END) as picks_b,
                    COUNT(*) as total_picks
                FROM predictions p
                WHERE p.fight_id = ?
                AND p.qa_status = 'approved'
            """, (fight_id,))

            result = cursor.fetchone()
            picks_a, picks_b, total_picks = result if result else (0, 0, 0)

            if total_picks >= 5:  # Need at least 5 predictions to identify underdogs
                # Identify underdog (less popular pick)
                underdog_is_a = picks_a < picks_b
                underdog_fighter = fighter_a if underdog_is_a else fighter_b
                underdog_pick = 'fighter_a' if underdog_is_a else 'fighter_b'
                underdog_count = picks_a if underdog_is_a else picks_b
                favorite_count = picks_b if underdog_is_a else picks_a

                # Only include if underdog has at least 2 picks and less than 50%
                if underdog_count >= 2 and underdog_count < (total_picks / 2):
                    # Get high accuracy analysts picking underdog
                    cursor.execute("""
                        SELECT a.name, a.real_name, a.accuracy_rate, p.notes
                        FROM predictions p
                        JOIN analysts a ON p.analyst_id = a.id
                        WHERE p.fight_id = ?
                        AND p.pick = ?
                        AND a.accuracy_rate >= 60
                        AND p.qa_status = 'approved'
                        ORDER BY a.accuracy_rate DESC
                    """, (fight_id, underdog_pick))

                    high_accuracy_analysts = []
                    for row in cursor.fetchall():
                        high_accuracy_analysts.append({
                            'name': row[1] or row[0],
                            'accuracy': row[2],
                            'reasoning': row[3]
                        })

                    # Get context tags for underdog
                    cursor.execute("""
                        SELECT p.context_tags
                        FROM predictions p
                        WHERE p.fight_id = ?
                        AND p.pick = ?
                        AND p.context_tags IS NOT NULL
                        AND p.qa_status = 'approved'
                    """, (fight_id, underdog_pick))

                    all_tags = []
                    for row in cursor.fetchall():
                        if row[0]:
                            try:
                                tags = json.loads(row[0])
                                all_tags.extend(tags)
                            except:
                                pass

                    top_tags = Counter(all_tags).most_common(3)

                    underdog_picks.append({
                        'fight': f"{fighter_a} vs {fighter_b}",
                        'fighter_a': fighter_a,
                        'fighter_b': fighter_b,
                        'underdog': underdog_fighter,
                        'underdog_count': underdog_count,
                        'favorite_count': favorite_count,
                        'total_predictions': total_picks,
                        'underdog_percentage': (underdog_count / total_picks) * 100,
                        'high_accuracy_analysts': high_accuracy_analysts,
                        'value_score': len(high_accuracy_analysts) / underdog_count if underdog_count > 0 else 0,
                        'top_tags': [{'tag': tag, 'count': count} for tag, count in top_tags]
                    })

        conn.close()

        # Sort by value score (high accuracy analysts per underdog pick)
        underdog_picks.sort(key=lambda x: x['value_score'], reverse=True)

        return {
            'event': event_name,
            'results_entered': bool(results_entered),
            'underdog_picks': underdog_picks
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
