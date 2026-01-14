#!/usr/bin/env python3
"""
Standalone script to create ChatMMA sample database.
Copy this entire file and run it anywhere you have Python 3.
No dependencies needed - just Python's built-in sqlite3.
"""
import sqlite3
import json
from pathlib import Path

# Create data directory
Path("data").mkdir(exist_ok=True)
db_path = "data/chatmma.db"

print(f"Creating database at: {db_path}")

# Remove old database if exists
import os
if os.path.exists(db_path):
    os.remove(db_path)

# Create connection
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create schema
print("Creating tables...")
cursor.executescript("""
-- Events table
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    date DATE NOT NULL,
    location TEXT,
    results_entered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fights table
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

-- Analysts table
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

-- Predictions table
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

-- Fight summaries table
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

-- Event accuracy table
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

-- Tag dictionary table
CREATE TABLE context_tag_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL UNIQUE,
    category TEXT,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_fights_event ON fights(event_id);
CREATE INDEX idx_predictions_fight ON predictions(fight_id);
CREATE INDEX idx_predictions_analyst ON predictions(analyst_id);
CREATE INDEX idx_event_accuracy_analyst ON event_accuracy(analyst_id);
CREATE INDEX idx_event_accuracy_event ON event_accuracy(event_id);
""")

print("Adding sample data...")

# Add events
cursor.execute("INSERT INTO events (name, date, location, results_entered) VALUES ('UFC Vegas 112', '2025-01-18', 'Las Vegas, Nevada', 0)")
vegas_id = cursor.lastrowid

cursor.execute("INSERT INTO events (name, date, location, results_entered) VALUES ('UFC 323', '2024-12-06', 'Las Vegas, Nevada', 1)")
ufc323_id = cursor.lastrowid

# Add analysts
analysts_data = [
    ('Analyst_001', 'Alexander K. Lee', 'article', 'MMA Fighting', 45, 32, 71.1),
    ('Analyst_002', 'Drake Riggs', 'article', 'Yahoo Sports', 38, 24, 63.2),
    ('Analyst_003', 'Christopher Olson', 'article', 'RotoWire', 42, 28, 66.7),
    ('Analyst_004', 'Tim Bissell', 'article', 'MMA Mania', 40, 26, 65.0),
    ('Analyst_005', 'The MMA Guru', 'youtube', 'The MMA Guru', 50, 28, 56.0),
    ('Analyst_006', 'Dan Hardy', 'youtube', 'Heavy Hands', 35, 25, 71.4),
    ('Analyst_007', 'John McCarthy', 'youtube', 'Weighing In', 48, 31, 64.6),
]

analyst_ids = {}
for name, real_name, type_, pub, total, correct, acc in analysts_data:
    cursor.execute("""
        INSERT INTO analysts (name, real_name, type, publication, total_predictions, correct_predictions, accuracy_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, real_name, type_, pub, total, correct, acc))
    analyst_ids[name] = cursor.lastrowid

# UFC Vegas 112 - Fight 1: Kape vs Royval
cursor.execute("""
    INSERT INTO fights (event_id, fighter_a, fighter_b, weight_class, is_main_card, scheduled_rounds)
    VALUES (?, 'Manel Kape', 'Brandon Royval', 'Flyweight', 1, 5)
""", (vegas_id,))
kape_royval_id = cursor.lastrowid

# Predictions for Kape vs Royval
kape_predictions = [
    (analyst_ids['Analyst_001'], 'fighter_a', 'high', 'DEC',
     json.dumps(['kape_wrestling_advantage', 'kape_sub_defense', 'kape_composure', 'royval_off_back']),
     "Kape's wrestling will neutralize Royval's chaotic grappling. His submission defense is strong enough to stay safe if Royval pulls guard, and his composure in extended scrambles gives him the edge over 5 rounds."),
    (analyst_ids['Analyst_002'], 'fighter_a', 'medium', 'DEC',
     json.dumps(['kape_wrestling', 'kape_cardio', 'royval_unpredictable']),
     "Kape's cardio and wrestling pace should overwhelm Royval over 5 rounds. While Royval is dangerous and unpredictable, Kape has shown he can avoid submissions and grind out decisions."),
    (analyst_ids['Analyst_003'], 'fighter_b', 'medium', 'SUB',
     json.dumps(['royval_submissions', 'royval_creativity', 'kape_grappling_vulnerable']),
     "Royval's unorthodox submission game could catch Kape. He's extremely creative off his back and Kape has shown vulnerabilities in scrambles. Picking Royval by submission in rounds 3-4."),
    (analyst_ids['Analyst_004'], 'fighter_a', 'high', 'DEC',
     json.dumps(['kape_wrestling_control', 'kape_experience', 'stylistic_favors_kape']),
     "This is a stylistic mismatch favoring Kape. His wrestling control and experience at this level will be too much for Royval's chaotic style. Expect Kape to dominate positionally."),
    (analyst_ids['Analyst_005'], 'fighter_a', 'low', 'DEC',
     json.dumps(['kape_power', 'royval_chin_suspect']),
     "Kape has more power and Royval's chin has been suspect. If Kape can avoid the scrambles, he should win on the feet or by grinding out a decision."),
    (analyst_ids['Analyst_006'], 'fighter_b', 'medium', 'SUB',
     json.dumps(['royval_submission_threat', 'royval_pace', 'kape_sub_defense_overrated']),
     "Royval's pace and submission threats will overwhelm Kape. I think Kape's submission defense is overrated - Royval finds a triangle or guillotine in the chaos."),
    (analyst_ids['Analyst_007'], 'fighter_a', 'medium', 'DEC',
     json.dumps(['kape_tactical', 'kape_fight_iq', 'royval_predictable']),
     "Kape is the more tactical fighter with higher fight IQ. He'll implement a gameplan to neutralize Royval's strengths and win a clear decision."),
]

for pred in kape_predictions:
    cursor.execute("""
        INSERT INTO predictions (fight_id, analyst_id, pick, confidence, method, context_tags, notes, extraction_confidence, qa_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 95, 'approved')
    """, (kape_royval_id,) + pred)

# UFC Vegas 112 - Fight 2: Font vs Phillips
cursor.execute("""
    INSERT INTO fights (event_id, fighter_a, fighter_b, weight_class, is_main_card, scheduled_rounds)
    VALUES (?, 'Rob Font', 'Kyler Phillips', 'Bantamweight', 1, 3)
""", (vegas_id,))
font_phillips_id = cursor.lastrowid

font_predictions = [
    (analyst_ids['Analyst_001'], 'fighter_a', 'high', 'DEC',
     json.dumps(['font_boxing', 'font_experience', 'phillips_youth']),
     "Font's boxing and experience edge should carry him. Phillips is talented but Font's technical striking will win him rounds consistently."),
    (analyst_ids['Analyst_002'], 'fighter_b', 'medium', 'DEC',
     json.dumps(['phillips_wrestling', 'phillips_pressure', 'font_aging']),
     "Phillips' youth, wrestling, and pressure could overwhelm an aging Font. Font's best years are behind him and Phillips is hungry."),
    (analyst_ids['Analyst_003'], 'fighter_a', 'medium', 'KO',
     json.dumps(['font_striking_technical', 'font_combinations', 'phillips_defense_holes']),
     "Font's technical striking and combination work will break down Phillips. Look for Font to land a clean counter for the finish."),
    (analyst_ids['Analyst_005'], 'fighter_b', 'high', 'DEC',
     json.dumps(['phillips_versatile', 'phillips_cardio', 'font_decline']),
     "Phillips is more versatile and has better cardio. Font is declining and Phillips will showcase his skills for a clear decision."),
    (analyst_ids['Analyst_006'], 'fighter_a', 'medium', 'DEC',
     json.dumps(['font_level_of_competition', 'font_boxing_defense']),
     "Font has faced much tougher competition. His boxing defense and ring generalship will frustrate Phillips for a decision win."),
]

for pred in font_predictions:
    cursor.execute("""
        INSERT INTO predictions (fight_id, analyst_id, pick, confidence, method, context_tags, notes, extraction_confidence, qa_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 95, 'approved')
    """, (font_phillips_id,) + pred)

# UFC 323 - Past event - Merab vs Yan
cursor.execute("""
    INSERT INTO fights (event_id, fighter_a, fighter_b, weight_class, is_main_card, scheduled_rounds, result, method, round)
    VALUES (?, 'Merab Dvalishvili', 'Petr Yan', 'Bantamweight', 1, 5, 'fighter_a_win', 'DEC_U', 5)
""", (ufc323_id,))
merab_yan_id = cursor.lastrowid

merab_predictions = [
    (analyst_ids['Analyst_001'], 'fighter_a', 'high', 'DEC',
     json.dumps(['merab_cardio', 'merab_wrestling', 'merab_pressure']),
     "Merab's relentless pace and wrestling will overwhelm Yan. His cardio is elite and Yan will fade in championship rounds."),
    (analyst_ids['Analyst_002'], 'fighter_a', 'medium', 'DEC',
     json.dumps(['merab_pace', 'yan_defensive_striking']),
     "Merab's pace wins this. Yan's defensive striking keeps it competitive but Merab's output over 5 rounds is too much."),
    (analyst_ids['Analyst_003'], 'fighter_b', 'medium', 'DEC',
     json.dumps(['yan_striking_precision', 'yan_counter_striking', 'merab_hittable']),
     "Yan's precision striking will pick Merab apart. Merab is hittable and Yan's counter-striking wins him the decision."),
    (analyst_ids['Analyst_006'], 'fighter_a', 'high', 'DEC',
     json.dumps(['merab_wrestling_pressure', 'merab_relentless']),
     "Merab is relentless and his wrestling pressure will break Yan's will. Clear decision victory for Merab."),
]

for pred in merab_predictions:
    cursor.execute("""
        INSERT INTO predictions (fight_id, analyst_id, pick, confidence, method, context_tags, notes, extraction_confidence, qa_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 95, 'approved')
    """, (merab_yan_id,) + pred)

conn.commit()
conn.close()

print("\n✅ Database created successfully!")
print(f"\n📁 Location: {db_path}")
print("\n📊 Contents:")
print("  • 2 events (UFC Vegas 112 upcoming, UFC 323 past)")
print("  • 3 fights with 16 predictions total")
print("  • 7 analysts with realistic accuracy rates")
print("\nReady to upload to GitHub!")
