# ChatMMA Development Plan (v4.1 - FINAL)
## Project Overview

**Mission:** Build an AI-powered chatbot that synthesizes publicly available MMA predictions from written articles AND curated YouTube videos to provide consensus insights, DFS strategy recommendations, and accumulated fighter intelligence.

**Timeline:** MVP ready before UFC 323 (January 24, 2026) - 16 days

**Budget Constraint:** $28/month maximum operational cost

**Content Strategy:** Hybrid approach - Written articles (4 sources) + Curated YouTube videos (3-5 sources)

**Testing Strategy:** Backfill UFC 313-321 with results, process UFC Vegas 112 WITHOUT results to test ChatMMA's predictive accuracy before launch

**Development Philosophy:** KISS (Keep It Simple, Stupid) - Minimal dependencies, tight scripts, no unnecessary abstraction, ship fast and iterate

---

## Development Philosophy (NEW)

**Core Principles:**

1. **KISS above all else**
   - Maximum 7 external dependencies
   - Scripts under 200 lines each
   - No abstraction until 3+ examples of the same pattern
   - Flat structure over nested complexity

2. **Explicit over implicit**
   - Pass parameters, don't auto-detect
   - One way to do each thing
   - Clear CLI commands

3. **Simple over clever**
   - Raw SQL > ORM
   - print() or basic logging > logging frameworks
   - YAML > complex config systems
   - Copy/paste > premature DRY

4. **Solve today's problem**
   - Building for 7-9 sources, not 100 sources
   - CLI tool now, web interface later
   - Manual testing fine for MVP

5. **Delete aggressively**
   - If you're not using it, delete it
   - No "we might need this later" code
   - Keep codebase lean

6. **Refactor based on reality**
   - Ship working MVP first
   - Learn from real usage
   - Then refactor with knowledge

---

## Core Features

### Feature 1: Extract Fight Picks from Multiple Source Types
Parse both written articles and YouTube video transcripts to extract structured predictions.

### Feature 2: Track Each Analyst's Record
Compare predictions to actual results after each event, calculating accuracy rates over time.

### Feature 3: Create Quality Scores for Each Analyst
Weight analyst opinions by historical accuracy when synthesizing answers.

### Feature 4: Learn About Fighters (Moderate Intelligence)
Extract and retain fighter-specific insights: traits, stylistic notes, DFS patterns, historical accuracy.

### Feature 5: Chat Interface
Allow users to ask natural language questions about fights, fighters, and DFS strategy.

### Feature 6: Self-Validation Testing
Test ChatMMA's accuracy against UFC Vegas 112 before public launch to validate the methodology.

---

## Technical Stack (LEAN)

### Absolute Minimum Dependencies (7 total):

```python
# Core (unavoidable)
anthropic              # Claude API
sqlite3                # Built-in to Python, no install needed
requests               # HTTP requests
pyyaml                 # Config files

# Content fetching
youtube-transcript-api # YouTube transcripts (no simpler alternative)
beautifulsoup4         # Article parsing (standard, minimal)

# Name matching
fuzzywuzzy             # Fighter name fuzzy matching
python-Levenshtein     # Makes fuzzywuzzy faster (optional but recommended)
```

**That's it. No ORMs, no frameworks, no complex architectures.**

### What We're NOT Using:

- ❌ SQLAlchemy or any ORM (raw SQL is simpler)
- ❌ FastAPI/Flask (not needed for CLI)
- ❌ Pandas (overkill for our use case)
- ❌ Complex logging frameworks (print/basic logging is fine)
- ❌ Testing frameworks for MVP (manual testing sufficient)
- ❌ Any "might need later" dependencies

---

## Project Structure (FLAT)

```
chatmma/
├── data/
│   ├── articles/              # Raw article text (kept for debugging)
│   ├── transcripts/           # YouTube transcripts (kept for debugging)
│   ├── extractions/           # AI-extracted picks (JSON) - ALWAYS KEEP
│   ├── raw_outputs/           # Raw Claude responses - ALWAYS KEEP
│   └── chatmma.db             # SQLite database
│
├── scripts/                   # All scripts in one flat directory
│   ├── utils.py               # Minimal shared utilities (5-6 functions only)
│   ├── fetch_articles.py      # Fetch article content (~50 lines)
│   ├── fetch_youtube.py       # Fetch YouTube transcripts (~50 lines)
│   ├── extract_picks.py       # Extract predictions (~150 lines, handles both types)
│   ├── qa_review.py           # Human QA interface (~100 lines)
│   ├── load_to_db.py          # Populate database (~100 lines)
│   ├── input_results.py       # Interactive results entry (~150 lines)
│   ├── backfill_analyst.py    # Add historical analyst (~100 lines)
│   ├── update_fighter_profiles.py  # Refresh fighter intelligence (~100 lines)
│   ├── test_vegas_112.py      # Testing framework (~150 lines)
│   └── chat_interface.py      # User chat interface (~150 lines)
│
├── sources.yaml               # List of article URLs + YouTube URLs
├── fighter_aliases.yaml       # Fighter name mappings
├── fights.yaml                # Fight card data per event
├── config.yaml                # API keys, settings
└── README.md                  # Setup and usage instructions
```

**No nested directories. No src/extractors/providers/. Keep it flat.**

---

## Database Schema (Enhanced with event_date)

```sql
-- Events table
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,           -- "UFC 323" or "UFC Vegas 112"
    date DATE NOT NULL,            -- "2026-01-24" (ADDED - for historical context)
    location TEXT,                 -- "Las Vegas, Nevada" (optional)
    fights_count INTEGER,
    results_entered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fights table
CREATE TABLE fights (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    fighter_a TEXT NOT NULL,      -- Canonical name
    fighter_b TEXT NOT NULL,      -- Canonical name
    result TEXT,                   -- "fighter_a_win", "fighter_b_win", "draw", NULL if not fought
    method TEXT,                   -- "KO", "TKO", "SUB", "DEC_U", "DEC_S", "DEC_M", "DQ", "NC", NULL
    round INTEGER,
    time TEXT,                     -- "3:47" (optional)
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- Sources table
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,            -- "Analyst #1" (anonymous)
    type TEXT NOT NULL,            -- "article" or "youtube"
    publication TEXT,              -- "Sherdog" or "Heavy Hands" (channel name)
    url TEXT,
    credibility_score REAL,        -- Calculated from historical accuracy
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate REAL
);

-- Predictions table
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    fight_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    prediction TEXT NOT NULL,      -- "fighter_a" or "fighter_b"
    method TEXT,                   -- "KO", "SUB", "DEC", NULL
    analyst_confidence TEXT,       -- "high", "medium", "low"
    extraction_confidence REAL,    -- 0-100 (AI confidence)
    reasoning TEXT,
    dfs_note TEXT,
    qa_status TEXT DEFAULT 'pending',  -- "approved", "pending", "rejected"
    raw_output_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fight_id) REFERENCES fights(id),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- Fighter context from predictions
CREATE TABLE prediction_context (
    id INTEGER PRIMARY KEY,
    prediction_id INTEGER NOT NULL,
    fighter_name TEXT NOT NULL,
    traits TEXT,                   -- Comma-separated: "grappler,cardio_issues"
    stylistic_notes TEXT,
    dfs_context TEXT,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

-- Fighter profiles built over time
CREATE TABLE fighter_profiles (
    id INTEGER PRIMARY KEY,
    fighter_name TEXT UNIQUE NOT NULL,
    total_mentions INTEGER DEFAULT 0,
    traits_json TEXT,              -- JSON: {"grappler": 8, "cardio_issues": 3}
    common_strengths TEXT,
    common_weaknesses TEXT,
    dfs_notes_json TEXT,
    times_predicted_to_win INTEGER DEFAULT 0,
    times_actually_won INTEGER DEFAULT 0,
    prediction_accuracy REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historical accuracy per event
CREATE TABLE accuracy (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    total_picks INTEGER,
    correct_picks INTEGER,
    accuracy_rate REAL,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- Testing results for validation
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    test_date DATE,
    chatmma_predictions TEXT,      -- JSON of what ChatMMA recommended
    actual_results TEXT,            -- JSON of actual outcomes
    accuracy_rate REAL,
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id)
);
```

---

## Minimal Shared Utilities

### `scripts/utils.py` (ONLY truly shared functions)

```python
"""
Minimal shared utilities.
Only add functions here if used by 3+ scripts.
"""
import re
import json
import yaml
from fuzzywuzzy import process

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&\s]+)',
        r'(?:youtu\.be\/)([^&\s]+)',
        r'(?:youtube\.com\/embed\/)([^&\s]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def match_fighter_name(extracted_name, canonical_fighters, aliases, threshold=85):
    """
    Match extracted fighter name to canonical name using aliases and fuzzy matching.
    Returns canonical name or None if no good match.
    """
    # Exact match
    if extracted_name in canonical_fighters:
        return extracted_name
    
    # Alias match
    for canonical, alias_list in aliases.items():
        if extracted_name.lower() in [a.lower() for a in alias_list]:
            return canonical
    
    # Fuzzy match
    best_match, score = process.extractOne(extracted_name, canonical_fighters)
    if score >= threshold:
        return best_match
    
    return None  # Flag for QA

def save_json(data, filepath):
    """Save JSON with error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")
        return False

def load_json(filepath):
    """Load JSON with error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON from {filepath}: {e}")
        return None

def load_yaml(filepath):
    """Load YAML config"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML from {filepath}: {e}")
        return None

def save_text(text, filepath):
    """Save text file with error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Error saving text to {filepath}: {e}")
        return False

# That's it. Nothing else until we need it.
```

**Rule: Don't add to utils.py unless the function is used by 3+ scripts.**

---

## Configuration Files

### `config.yaml`
```yaml
claude_api:
  extraction_model: "claude-haiku-4-5-20251001"  # Cost-effective
  chat_model: "claude-sonnet-4-20250514"         # Quality for users
  key: "YOUR_API_KEY"
  max_tokens: 1500

database:
  path: "data/chatmma.db"

qa:
  extraction_confidence_threshold: 70  # Flag below this

name_matching:
  fuzzy_threshold: 85  # Minimum similarity

fighter_profiles:
  min_mentions_for_profile: 3
  trait_significance_threshold: 3

youtube:
  transcript_languages: ["en"]
  max_transcript_length: 50000  # Skip very long videos

storage:
  keep_transcripts_after_qa: true    # Set false to auto-delete (NEW)
  keep_raw_outputs_always: true      # Always keep for debugging (NEW)
  cleanup_after_days: 60             # Auto-cleanup old files (NEW)

testing:
  holdout_event: "UFC Vegas 112"
```

### `sources.yaml` (Example)
```yaml
sources:
  # Written Articles
  - name: "Analyst_001"
    type: article
    publication: "Sherdog"
    url: "https://www.sherdog.com/news/articles/ufc-vegas-112-predictions"
    event: "UFC Vegas 112"
  
  - name: "Analyst_002"
    type: article
    publication: "ActionNetwork"
    url: "https://www.actionnetwork.com/mma/ufc-vegas-112-predictions"
    event: "UFC Vegas 112"
  
  # YouTube Videos
  - name: "Analyst_005"
    type: youtube
    channel: "Heavy Hands"
    url: "https://www.youtube.com/watch?v=XXXXX"
    event: "UFC Vegas 112"
  
  - name: "Analyst_006"
    type: youtube
    channel: "The Weasle"
    url: "https://www.youtube.com/watch?v=YYYYY"
    event: "UFC Vegas 112"
```

### `fighter_aliases.yaml`
```yaml
canonical_names:
  "Brandon Royval":
    - "Royval"
    - "Brandon"
    - "B Royval"
    - "Royal"  # Common transcript error
  
  "Manel Kape":
    - "Kape"
    - "Manel"
    - "Starboy"
  
  # Add more as discovered during processing
```

### `fights.yaml` (Per Event)
```yaml
event: "UFC Vegas 112"
date: "2026-01-18"  # ADDED - now required
location: "Las Vegas, Nevada"

fights:
  - fighter_a: "Brandon Royval"
    fighter_b: "Manel Kape"
    weight_class: "Flyweight"
    is_main_card: true
    scheduled_rounds: 3
    # Results added via input_results.py after event
  
  - fighter_a: "Giga Chikadze"
    fighter_b: "Kevin Vallejos"
    weight_class: "Featherweight"
    is_main_card: true
    scheduled_rounds: 3
```

---

## Phase 1: Content Fetching (Week 1)

### Part A: Article Fetching

**Script: `fetch_articles.py`** (~50 lines)

**Single responsibility:** Fetch article text and save to files.

**Usage:**
```bash
python scripts/fetch_articles.py --sources sources.yaml --event "UFC Vegas 112"
```

**What it does:**
1. Reads sources.yaml for `type: article` entries
2. Fetches HTML for each URL
3. Extracts main content (beautifulsoup4)
4. Saves to `data/articles/{event}_{analyst_name}.txt`
5. Logs success/failure

**Keep it under 50 lines.** No complex error handling, just try/except and log.

### Part B: YouTube Transcript Fetching

**Script: `fetch_youtube.py`** (~50 lines)

**Single responsibility:** Fetch YouTube transcripts and save to files.

**Library:** `youtube-transcript-api` (FREE, no API key)

**Usage:**
```bash
python scripts/fetch_youtube.py --sources sources.yaml --event "UFC Vegas 112"
```

**What it does:**
1. Reads sources.yaml for `type: youtube` entries
2. Extracts video ID using `utils.extract_video_id()`
3. Fetches transcript using library
4. Saves to `data/transcripts/{event}_{analyst_name}.txt`
5. Logs success/failure

**Simple example:**
```python
from youtube_transcript_api import YouTubeTranscriptApi
from utils import extract_video_id, save_text, load_yaml

def main():
    sources = load_yaml('sources.yaml')
    
    for source in sources['sources']:
        if source['type'] != 'youtube':
            continue
            
        video_id = extract_video_id(source['url'])
        if not video_id:
            print(f"Invalid URL: {source['url']}")
            continue
        
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = ' '.join([entry['text'] for entry in transcript])
            
            filename = f"data/transcripts/{source['event']}_{source['name']}.txt"
            save_text(full_text, filename)
            print(f"✓ Saved: {filename}")
            
        except Exception as e:
            print(f"✗ Failed: {source['name']} - {e}")
```

**That's it. ~50 lines total.**

---

## Phase 2: Pick Extraction (Week 1-2)

**Script: `extract_picks.py`** (~150 lines, handles both types)

**Single responsibility:** Extract predictions from any content type.

**Usage:**
```bash
python scripts/extract_picks.py --event "UFC Vegas 112" --fights fights.yaml --aliases fighter_aliases.yaml
```

**What it does:**
1. Reads all files in `data/articles/` and `data/transcripts/` for this event
2. For each file, sends to Claude API (Haiku) with extraction prompt
3. Parses JSON response
4. Matches fighter names using `utils.match_fighter_name()`
5. Saves to `data/extractions/{event}_{analyst}.json`
6. Saves raw Claude output to `data/raw_outputs/{event}_{analyst}_{timestamp}.txt`
7. Flags low-confidence extractions

**No complex class hierarchies. Just:**
```python
def extract_from_content(content, event_info, content_type):
    """Send content to Claude, return structured predictions"""
    # Build prompt
    # Call Claude API
    # Parse response
    # Return predictions

def process_event(event_name):
    """Process all sources for an event"""
    # Load config
    # For each article: extract_from_content()
    # For each transcript: extract_from_content()
    # Save results
```

**One file, straightforward flow, ~150 lines.**

---

## Phase 3-10: (Same structure)

All remaining phases follow the same philosophy:
- One script per job
- Under 200 lines each
- Minimal abstraction
- Clear CLI interface

**Key scripts:**
- `qa_review.py` (~100 lines) - Interactive review
- `load_to_db.py` (~100 lines) - Raw SQL inserts
- `input_results.py` (~150 lines) - Interactive or CSV
- `update_fighter_profiles.py` (~100 lines) - Aggregate from DB
- `test_vegas_112.py` (~150 lines) - Testing framework
- `chat_interface.py` (~150 lines) - Query DB + Claude synthesis

**Total codebase: ~1200 lines excluding utils**

---

## Storage Strategy (Clarified)

**What to keep:**
- ✅ **Always keep:** `extractions/` (JSON predictions)
- ✅ **Always keep:** `raw_outputs/` (Claude responses for debugging)
- ✅ **Keep during development:** `articles/` and `transcripts/`
- ⚠️ **Optional cleanup post-launch:** Delete old articles/transcripts after 1-2 events

**Why keep transcripts:**
1. Debugging extraction failures
2. Refining prompts later
3. Reprocessing without re-fetching
4. Cost: negligible (~3MB for 50 transcripts)

**Optional cleanup script** (not needed for MVP):
```python
# scripts/cleanup.py (optional, post-launch)
def cleanup_old_content(keep_events=2):
    """Delete articles/transcripts older than N events"""
    # Keep most recent 2 events
    # Delete older content
    # Never delete extractions or raw_outputs
```

**Decision: Keep everything during MVP. Add cleanup post-launch if needed.**

---

## Source Strategy

### Tier 1: Written Articles (4 sources - you have these)
From your CSV tracker

### Tier 2: Curated YouTube (3-5 sources recommended)

**Must include:**
1. **Heavy Hands** - Technical, analytical
2. **The Weasle** - Consistent, accessible

**Recommended:**
3. **Dan Tom** - Sharp analyst (if available)
4. **Cody Saftic** - DFS-focused (if available)
5. **[1-2 more you trust]**

**Selection criteria:**
- ✅ Clear predictions every event
- ✅ Transcripts available
- ✅ 15-60 minute videos (not 2+ hour podcasts)
- ✅ Makes actual picks (not just analysis)

**Total: 7-9 sources (4 articles + 3-5 videos)**

---

## Development Workflow

### Week 1: Foundation
**Days 1-2:**
- Set up project structure
- Install 7 dependencies
- Create config files
- Create minimal `utils.py`

**Days 3-4:**
- Build `fetch_articles.py` (~50 lines)
- Build `fetch_youtube.py` (~50 lines)
- Test with 2-3 sources

**Days 5-7:**
- Build `extract_picks.py` (~150 lines)
- Test extraction on articles
- Test extraction on transcripts
- Refine extraction prompt

### Week 2: QA & Database
**Days 8-9:**
- Build `qa_review.py` (~100 lines)
- Set up SQLite database (raw SQL, no ORM)
- Build `load_to_db.py` (~100 lines)

**Days 10-11:**
- Build `input_results.py` (~150 lines)
- Build `update_fighter_profiles.py` (~100 lines)
- Process 1-2 test events end-to-end

**Days 12-14:**
- Build `backfill_analyst.py` (~100 lines)
- Test complete workflow
- Expand `fighter_aliases.yaml` as needed

### Week 3: Historical Data
**Days 15-18:**
- Backfill UFC 313-321 (9 events with results)
- Process Vegas 112 (no results)
- QA review all flagged items
- Calculate historical accuracy

**Days 19-21:**
- Build fighter profiles from historical data
- Verify data quality
- Build `test_vegas_112.py` (~150 lines)

### Week 4: Testing & Launch
**Days 22-24:**
- Build `chat_interface.py` (~150 lines)
- Generate Vegas 112 predictions via ChatMMA
- Test chat responses

**Days 25-26:**
- Wait for Vegas 112 event
- Input results
- Run accuracy analysis

**Day 27:**
- If accuracy ≥ 60%: Proceed
- If accuracy < 60%: Debug and fix

**Days 28-30:**
- Polish chat responses
- Process UFC 323 predictions
- Soft launch with beta users

---

## Cost Analysis

**Monthly operational cost:**

**Claude Code:** $20/month (what you just subscribed to)

**Claude API:**
- Haiku extraction: 4 events × $0.024 = $0.10/month
- Sonnet chat: 4 events × $1.50 = $6.00/month
- **Total API:** $6.10/month

**Everything else:** $0

**Total: $26.10/month** ✅ Under budget

---

## Success Metrics

**Vegas 112 Test:**
- ✅ Minimum: 60% accuracy (better than random)
- ✅ Good: 65% accuracy (competitive)
- ✅ Excellent: 70% accuracy (better than most analysts)
- ✅ Bonus: Beat simple consensus (validates weighting)

**Technical:**
- ✅ All scripts under 200 lines
- ✅ Total codebase under 1500 lines
- ✅ 7 dependencies only
- ✅ QA takes < 12 min/event
- ✅ Results input < 3 min/event

**Business:**
- ✅ ChatMMA provides unique value
- ✅ Users save hours of research
- ✅ Response quality shareable publicly

---

## Key Principles (Summary)

**When in doubt:**
1. **Keep it simple** - Can you do it in fewer lines?
2. **Keep it explicit** - Is it clear what this does?
3. **Keep it lean** - Do you really need this dependency/abstraction?
4. **Ship it** - Is it good enough to test with real users?

**Red flags:**
- Script over 200 lines → consider splitting (but only if natural break)
- Adding 8th dependency → really necessary?
- Creating abstraction → do you have 3+ examples?
- Complex config → can YAML handle this?

**Green lights:**
- Copy/paste code → fine for MVP
- print() for logging → fine for MVP
- Manual testing → fine for MVP
- Flat structure → always good

---

## Getting Started Checklist

- [x] Subscribed to Claude Pro ($20/month) ✅
- [ ] Get Claude API key (console.anthropic.com)
- [ ] Identify 3-5 YouTube channels
- [ ] Create `sources.yaml` with all sources
- [ ] Create `fights.yaml` for UFC 313-322 with dates
- [ ] Gather fight results for UFC 313-321 (NOT Vegas 112)
- [ ] Create `fighter_aliases.yaml` (start minimal)
- [ ] Create `config.yaml` with API key
- [ ] Install 7 dependencies
- [ ] Create project structure
- [ ] Build `utils.py` with 6 functions
- [ ] Begin Phase 1: fetch_articles.py

---

## What Changed in v4.1

**Additions from v4:**

1. ✅ **Development Philosophy section**
   - KISS principles documented
   - 7-dependency limit
   - No abstraction until 3+ examples
   - Scripts under 200 lines

2. ✅ **event_date field added to database**
   - Required for historical queries
   - Enables timeline features
   - Helps with validation

3. ✅ **Minimal utils.py defined**
   - Exactly 6 functions
   - Only add if used by 3+ scripts
   - Prevents premature abstraction

4. ✅ **Storage strategy clarified**
   - Keep transcripts during development
   - Optional cleanup post-launch
   - Never delete extractions/raw_outputs

5. ✅ **Line count targets for each script**
   - Clear size expectations
   - Prevents scope creep
   - Total codebase: ~1200 lines

6. ✅ **"What NOT to use" list**
   - Explicit about avoiding ORMs, frameworks
   - Prevents over-engineering
   - Keeps stack minimal

7. ✅ **Flat structure emphasized**
   - No nested directories
   - One script per job
   - Easy to navigate

**Philosophy:** Ship a working MVP in 16 days. Refactor based on real usage patterns, not imagined future needs.

---

## Final Notes

**You now have:**
- ✅ Complete, production-ready plan
- ✅ KISS philosophy baked in
- ✅ Minimal dependencies (7 total)
- ✅ Lean codebase (~1200 lines)
- ✅ Clear size targets per script
- ✅ Vegas 112 validation framework
- ✅ Within budget ($26/month)
- ✅ 16-day timeline

**This plan is ready to hand to Claude Code.**

**Next step:** Start building Phase 1 with Claude Code. Create the project structure, build utils.py, then build fetch_articles.py and fetch_youtube.py.

**Good luck! 🚀**