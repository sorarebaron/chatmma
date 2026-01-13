-- ChatMMA Enhanced Database Schema v2.0
-- Optimized for context tags, reasoning, and cost-efficient queries

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    date DATE NOT NULL,
    location TEXT,
    results_entered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fights table
CREATE TABLE IF NOT EXISTS fights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    fighter_a TEXT NOT NULL,
    fighter_b TEXT NOT NULL,
    weight_class TEXT,
    is_main_card BOOLEAN DEFAULT 0,
    scheduled_rounds INTEGER DEFAULT 3,
    result TEXT,  -- "fighter_a_win", "fighter_b_win", "draw", NULL
    method TEXT,  -- "KO", "TKO", "SUB", "DEC_U", "DEC_S", "DEC_M", NULL
    round INTEGER,
    time TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Analysts table (formerly sources)
CREATE TABLE IF NOT EXISTS analysts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,  -- "Analyst_001", etc.
    real_name TEXT,  -- "Alexander K. Lee" (revealed after event)
    type TEXT NOT NULL,  -- "article" or "youtube"
    publication TEXT,  -- "MMA Fighting", "Heavy Hands", etc.
    url TEXT,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Predictions table (ENHANCED with context_tags and notes)
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fight_id INTEGER NOT NULL,
    analyst_id INTEGER NOT NULL,
    pick TEXT NOT NULL,  -- "fighter_a" or "fighter_b"
    confidence TEXT,  -- "high", "medium", "low"
    method TEXT,  -- "KO", "SUB", "DEC", "FINISH", NULL
    context_tags TEXT,  -- JSON array: ["kape_wrestling_advantage", "kape_sub_defense"]
    notes TEXT,  -- Full rationale in natural language
    extraction_confidence REAL DEFAULT 100.0,
    qa_status TEXT DEFAULT 'approved',  -- "approved", "pending", "rejected"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES fights(id) ON DELETE CASCADE,
    FOREIGN KEY (analyst_id) REFERENCES analysts(id) ON DELETE CASCADE
);

-- Fight summaries (pre-generated for cost optimization)
CREATE TABLE IF NOT EXISTS fight_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fight_id INTEGER NOT NULL UNIQUE,
    total_predictions INTEGER DEFAULT 0,
    fighter_a_picks INTEGER DEFAULT 0,
    fighter_b_picks INTEGER DEFAULT 0,
    top_tags_fighter_a TEXT,  -- JSON: [{"tag": "kape_wrestling", "count": 9}]
    top_tags_fighter_b TEXT,  -- JSON: [{"tag": "royval_submissions", "count": 4}]
    consensus_summary TEXT,  -- Pre-generated summary for quick responses
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES fights(id) ON DELETE CASCADE
);

-- Historical accuracy per event
CREATE TABLE IF NOT EXISTS event_accuracy (
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

-- Tag dictionary (tracks all context tags used)
CREATE TABLE IF NOT EXISTS context_tag_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL UNIQUE,
    category TEXT,  -- "wrestling", "striking", "cardio", "grappling", etc.
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fights_event ON fights(event_id);
CREATE INDEX IF NOT EXISTS idx_predictions_fight ON predictions(fight_id);
CREATE INDEX IF NOT EXISTS idx_predictions_analyst ON predictions(analyst_id);
CREATE INDEX IF NOT EXISTS idx_event_accuracy_analyst ON event_accuracy(analyst_id);
CREATE INDEX IF NOT EXISTS idx_event_accuracy_event ON event_accuracy(event_id);
