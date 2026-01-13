"""
Load fight data and predictions into SQLite database
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import sqlite3
import glob
from utils import load_config, load_yaml, load_json, log

def load_events_and_fights():
    """Load events and fights from fights.yaml into database"""
    config = load_config()
    conn = sqlite3.connect(config['database']['path'])
    cursor = conn.cursor()

    fights_data = load_yaml('fights.yaml')

    for event in fights_data['events']:
        # Insert event
        cursor.execute('''
            INSERT OR IGNORE INTO events (name, date, location, fights_count)
            VALUES (?, ?, ?, ?)
        ''', (event['name'], event['date'], event['location'], len(event['fights'])))

        # Get event ID
        cursor.execute('SELECT id FROM events WHERE name = ?', (event['name'],))
        event_id = cursor.fetchone()[0]

        # Insert fights
        for fight in event['fights']:
            cursor.execute('''
                INSERT OR IGNORE INTO fights
                (event_id, fighter_a, fighter_b, weight_class, is_main_card,
                 scheduled_rounds, result, method, round, time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                fight['fighter_a'],
                fight['fighter_b'],
                fight['weight_class'],
                fight.get('is_main_card', False),
                fight.get('scheduled_rounds', 3),
                fight.get('result'),
                fight.get('method'),
                fight.get('round'),
                fight.get('time')
            ))

    conn.commit()
    conn.close()
    log("Events and fights loaded into database")

def load_sources():
    """Load sources from sources.yaml into database"""
    config = load_config()
    conn = sqlite3.connect(config['database']['path'])
    cursor = conn.cursor()

    sources = load_yaml('sources.yaml')['sources']

    for source in sources:
        cursor.execute('''
            INSERT OR IGNORE INTO sources (name, type, publication, analyst, url)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source['name'],
            source['type'],
            source.get('publication', ''),
            source.get('analyst', ''),
            source['url']
        ))

    conn.commit()
    conn.close()
    log(f"Loaded {len(sources)} sources into database")

def load_predictions(event_name=None):
    """Load extracted predictions from JSON files into database"""
    config = load_config()
    conn = sqlite3.connect(config['database']['path'])
    cursor = conn.cursor()

    # Find all extraction files
    extraction_dir = 'data/extractions'
    if event_name:
        pattern = f"{extraction_dir}/*{event_name.replace(' ', '_')}*_extraction.json"
    else:
        pattern = f"{extraction_dir}/*_extraction.json"

    extraction_files = glob.glob(pattern)
    log(f"Found {len(extraction_files)} extraction files")

    total_loaded = 0

    for filepath in extraction_files:
        data = load_json(filepath)
        event = data['event']
        source_info = data['source']

        # Get source_id
        cursor.execute('SELECT id FROM sources WHERE name = ?', (source_info['name'],))
        result = cursor.fetchone()
        if not result:
            log(f"Source not found: {source_info['name']}", "WARNING")
            continue
        source_id = result[0]

        # Get event_id
        cursor.execute('SELECT id FROM events WHERE name = ?', (event,))
        result = cursor.fetchone()
        if not result:
            log(f"Event not found: {event}", "WARNING")
            continue
        event_id = result[0]

        # Load each prediction
        for pred in data['predictions']:
            # Find the fight
            cursor.execute('''
                SELECT id, fighter_a, fighter_b FROM fights
                WHERE event_id = ? AND fighter_a = ? AND fighter_b = ?
            ''', (event_id, pred['fighter_a'], pred['fighter_b']))

            result = cursor.fetchone()
            if not result:
                log(f"Fight not found: {pred['fighter_a']} vs {pred['fighter_b']}", "WARNING")
                continue
            fight_id, fighter_a, fighter_b = result

            # Convert pick from fighter name to fighter_a/fighter_b
            pick = pred.get('pick', '')
            if not pick:
                log(f"No pick found in prediction for {fighter_a} vs {fighter_b}", "WARNING")
                continue

            if pick == fighter_a or pick == 'fighter_a':
                prediction = 'fighter_a'
            elif pick == fighter_b or pick == 'fighter_b':
                prediction = 'fighter_b'
            else:
                # Try to match the pick to one of the fighters
                pick_lower = str(pick).lower()
                if fighter_a.lower() in pick_lower or pick_lower in fighter_a.lower():
                    prediction = 'fighter_a'
                elif fighter_b.lower() in pick_lower or pick_lower in fighter_b.lower():
                    prediction = 'fighter_b'
                else:
                    log(f"Could not match pick '{pick}' to fighters {fighter_a} vs {fighter_b}", "WARNING")
                    continue

            # Insert prediction
            cursor.execute('''
                INSERT OR REPLACE INTO predictions
                (fight_id, source_id, event_name, prediction, method,
                 analyst_confidence, extraction_confidence, reasoning,
                 dfs_note, qa_status, raw_output_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fight_id,
                source_id,
                event,
                prediction,
                pred.get('method'),
                pred.get('confidence'),
                pred.get('extraction_confidence'),
                pred.get('reasoning'),
                pred.get('dfs_note'),
                'approved',  # Auto-approve for testing
                filepath
            ))
            total_loaded += 1

    conn.commit()
    conn.close()
    log(f"Loaded {total_loaded} predictions into database")

def update_analyst_stats():
    """Calculate accuracy rates for all analysts"""
    config = load_config()
    conn = sqlite3.connect(config['database']['path'])
    cursor = conn.cursor()

    # Get all sources
    cursor.execute('SELECT id, name FROM sources')
    sources = cursor.fetchall()

    for source_id, source_name in sources:
        # Count total predictions
        cursor.execute('''
            SELECT COUNT(*) FROM predictions
            WHERE source_id = ? AND qa_status = 'approved'
        ''', (source_id,))
        total = cursor.fetchone()[0]

        # Count correct predictions
        cursor.execute('''
            SELECT COUNT(*) FROM predictions p
            JOIN fights f ON p.fight_id = f.id
            WHERE p.source_id = ?
            AND p.qa_status = 'approved'
            AND f.result IS NOT NULL
            AND (
                (p.prediction = 'fighter_a' AND f.result = 'fighter_a_win') OR
                (p.prediction = 'fighter_b' AND f.result = 'fighter_b_win')
            )
        ''', (source_id,))
        correct = cursor.fetchone()[0]

        # Calculate accuracy
        accuracy = (correct / total * 100) if total > 0 else 0

        # Update source
        cursor.execute('''
            UPDATE sources
            SET total_predictions = ?, correct_predictions = ?, accuracy_rate = ?
            WHERE id = ?
        ''', (total, correct, accuracy, source_id))

        log(f"Updated {source_name}: {correct}/{total} = {accuracy:.1f}%")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Load data into database')
    parser.add_argument('--events', action='store_true', help='Load events and fights')
    parser.add_argument('--sources', action='store_true', help='Load sources')
    parser.add_argument('--predictions', action='store_true', help='Load predictions')
    parser.add_argument('--event', help='Event name to filter by (optional)')
    parser.add_argument('--stats', action='store_true', help='Update analyst statistics')
    parser.add_argument('--all', action='store_true', help='Load everything')

    args = parser.parse_args()

    if args.all:
        load_events_and_fights()
        load_sources()
        load_predictions(args.event)
        update_analyst_stats()
    else:
        if args.events:
            load_events_and_fights()
        if args.sources:
            load_sources()
        if args.predictions:
            load_predictions(args.event)
        if args.stats:
            update_analyst_stats()

    print("✅ Database loading complete")
