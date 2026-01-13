# ChatMMA

AI-powered MMA predictions chatbot that synthesizes insights from multiple expert analysts.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
cd scripts
python init_database.py
```

### 3. Process an Event

For UFC 323 (or any event):

```bash
# Fetch articles and transcripts
python fetch_articles.py --event "UFC 323"
python fetch_youtube.py --event "UFC 323"

# Extract predictions using Claude
python extract_picks.py "UFC 323"

# Load into database
python load_to_db.py --all --event "UFC 323"
```

### 4. Chat Interface

```bash
python chat_interface.py
```

Example questions:
- "Who do analysts think will win UFC 323 main event?"
- "What are the predictions for Petr Yan vs Merab Dvalishvili?"
- "Which analysts are most accurate?"

## Project Structure

```
chatmma/
├── data/
│   ├── articles/         # Fetched article content
│   ├── transcripts/      # YouTube transcripts
│   ├── extractions/      # Extracted predictions (JSON)
│   ├── raw_outputs/      # Claude API responses
│   └── chatmma.db        # SQLite database
├── scripts/
│   ├── utils.py                    # Helper functions
│   ├── init_database.py            # Database setup
│   ├── fetch_articles.py           # Fetch articles
│   ├── fetch_youtube.py            # Fetch YouTube transcripts
│   ├── extract_picks.py            # Extract predictions with Claude
│   ├── load_to_db.py               # Load data into DB
│   └── chat_interface.py           # Interactive chat
├── config.yaml           # Configuration
├── sources.yaml          # Analyst sources
├── fights.yaml           # Fight cards
└── fighter_aliases.yaml  # Fighter name variations
```

## Workflow

1. **Fetch Content**: Download articles and YouTube transcripts
2. **Extract Predictions**: Use Claude to extract structured predictions
3. **Load to Database**: Populate SQLite database
4. **Chat**: Ask questions and get synthesized insights

## Configuration

Edit `config.yaml` to:
- Set Claude API key
- Adjust extraction confidence thresholds
- Configure YouTube transcript settings
- Set budget limits

## Data Files

- **sources.yaml**: List of analysts and their content URLs
- **fights.yaml**: Fight cards with fighters and results
- **fighter_aliases.yaml**: Map nicknames to canonical fighter names

## MVP Features

- ✅ Extract predictions from articles and YouTube
- ✅ Track analyst accuracy over time
- ✅ Weight predictions by analyst credibility
- ✅ Interactive chat interface
- ✅ Cost tracking for Claude API

## Testing

Use UFC Vegas 112 as holdout event:
1. Process all historical events (UFC 320-323)
2. Extract predictions for Vegas 112 WITHOUT results
3. Compare ChatMMA consensus to actual results
4. Measure accuracy before public launch

## Cost Tracking

Average cost per event: $0.10-0.20 (extraction) + $0.05-0.10 (queries)
Monthly budget: $28 (supports ~140 events worth of processing)

## Development Philosophy

KISS: Keep It Simple, Stupid
- Flat structure, minimal dependencies
- Raw SQL over ORMs
- CLI-first, ship fast
- Manual testing for MVP
