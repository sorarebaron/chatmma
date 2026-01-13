# ChatMMA v2.0 - Enhanced Architecture

**"ChatMMA knows who every public analyst picked. AMA!"**

An AI-powered chatbot that tracks MMA analyst predictions with context tags, reasoning, and cost-optimized queries.

## 🎯 Key Features

### ✅ What's New in v2.0

1. **Context Tags** - Structured tags for every prediction (e.g., `kape_wrestling_advantage`, `royval_submissions`)
2. **Reasoning Notes** - Full analyst rationale in natural language
3. **Cost Optimization** - Pre-filter database before sending to Claude (10x cheaper)
4. **Analyst Anonymity** - Don't reveal names before events
5. **Historical Tracking** - Track analyst accuracy over time
6. **Lean Prompts** - Focus on "why" analysts picked fighters, not just "who"

## 📊 Architecture Overview

```
User Question
     ↓
Query Optimizer (Python) ← Filters database, aggregates context
     ↓
Prompt Generator (Python) ← Builds lean, focused prompt
     ↓
Claude API ← Only receives relevant context (200-500 tokens)
     ↓
User Answer
```

**Cost savings:** ~$0.001 per query (vs $0.01 previously)

## 🗄️ Database Schema

Enhanced schema with:
- `predictions.context_tags` - JSON array of structured tags
- `predictions.notes` - Full analyst reasoning
- `fight_summaries` - Pre-computed summaries for instant responses
- `event_accuracy` - Per-event analyst performance tracking

See `schema.sql` for full details.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install anthropic pyyaml
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Initialize Database

```bash
python scripts/init_db.py
```

### 4. Load Event Data

```bash
# This will create events and fights from fights.yaml
python scripts/load_predictions.py --event "UFC 323" --fights fights.yaml
```

## 📥 Data Pipeline

### Step 1: Extract Predictions (with context tags)

```bash
# Extract from article or transcript
python scripts/extract_predictions.py \
  --event "UFC 323" \
  --content-file "data/articles/ufc_323_analyst_001.txt" \
  --fights fights.yaml
```

This extracts:
- Fighter pick
- Confidence level
- Expected method
- **Context tags** (e.g., `["kape_wrestling", "kape_sub_defense"]`)
- **Reasoning notes** (2-4 sentences explaining why)

### Step 2: Load Into Database

```bash
python scripts/load_predictions.py --event "UFC 323"
```

This loads all extraction JSONs from `data/extractions/` into the database.

### Step 3: Generate Summaries (Optional)

```bash
python scripts/update_stats.py --event "UFC 323" --action summaries
```

Pre-computes fight summaries for instant chatbot responses.

## 💬 Using the Chatbot

### Web Interface (Streamlit)

**Deployed at:** [chatmma.streamlit.app](https://chatmma.streamlit.app)

Run locally:
```bash
streamlit run streamlit_app.py
```

See [STREAMLIT_DEPLOYMENT.md](STREAMLIT_DEPLOYMENT.md) for deployment instructions.

### CLI Interactive Mode

```bash
python scripts/chatbot.py
```

```
🥊 You: Who will win between Kape and Royval?

🤖 ChatMMA: For the main event between Manel Kape and Brandon Royval,
15 analysts favor Kape with 9 expecting it to go the distance, while 5
pick Royval with 3 seeing a submission victory.

The consensus leans Kape primarily due to his wrestling advantage, which
9 analysts specifically mentioned. Many emphasized Kape's ability to
neutralize Royval's chaotic grappling and strong submission defense...

💰 Query cost: $0.0012 (450 tokens)
```

### Single Question Mode

```bash
python scripts/chatbot.py "Why do analysts favor Kape?"
```

## 🎨 Example Data Format

### Prediction with Context Tags

```json
{
  "fighter_a": "Manel Kape",
  "fighter_b": "Brandon Royval",
  "pick": "Manel Kape",
  "confidence": "high",
  "method": "DEC",
  "context_tags": [
    "kape_wrestling_advantage",
    "kape_sub_defense",
    "kape_composure",
    "royval_off_back",
    "stylistic_mismatch_favors_kape"
  ],
  "notes": "Dan from Best Fight Picks believes Kape's wrestling will neutralize Royval's chaotic grappling. He emphasized that Kape's submission defense is strong enough to stay safe if Royval pulls guard, and also mentioned Kape's composure in extended scrambles gives him the edge."
}
```

## 🏷️ Context Tag Guidelines

**Format:** `snake_case`

**Categories:**
- `{fighter}_wrestling_advantage`
- `{fighter}_striking_power`
- `{fighter}_cardio_edge`
- `{fighter}_sub_defense`
- `{fighter}_experience`
- `stylistic_mismatch_favors_{fighter}`

**Examples:**
- `jones_reach_advantage`
- `holloway_cardio`
- `oliveira_submission_threat`
- `ngannou_knockout_power`

## 📈 Updating Stats

### After Event Results

```bash
# Mark event as complete
sqlite3 data/chatmma.db "UPDATE events SET results_entered = 1 WHERE name = 'UFC 323'"

# Update fight results (manually or via script)
# Then update accuracy stats

python scripts/update_stats.py --event "UFC 323" --action accuracy
```

This calculates:
- Per-analyst accuracy for the event
- Overall analyst accuracy (all-time)
- Updates analyst credibility scores

## 🎯 Cost Optimization Details

### Traditional Approach (Expensive)
```
Question → Send ALL predictions to Claude (5000+ tokens) → $0.01 per query
```

### ChatMMA v2.0 (Optimized)
```
Question → Python filters DB → Send aggregated context (300-500 tokens) → $0.001 per query
```

**Savings:** 90% reduction in cost per query

### What Gets Pre-Filtered

1. **Pick distribution** (15 for Kape, 5 for Royval)
2. **Top context tags** (kape_wrestling: 9 mentions, kape_sub_defense: 7 mentions)
3. **Example rationales** (top 2-3 from high-accuracy analysts)
4. **Analyst tiers** (12 high-accuracy analysts picked Kape)

Claude receives focused context, not raw predictions.

## 📂 Project Structure

```
chatmma/
├── data/
│   ├── chatmma.db              # SQLite database
│   ├── articles/               # Raw article text
│   ├── transcripts/            # YouTube transcripts
│   └── extractions/            # Extracted predictions (JSON)
│
├── scripts/
│   ├── init_db.py              # Initialize database
│   ├── extract_predictions.py  # Extract with context tags
│   ├── load_predictions.py     # Load into database
│   ├── query_optimizer.py      # Cost-efficient filtering
│   ├── prompt_generator.py     # Lean prompt builder
│   ├── chatbot.py              # Main interface
│   └── update_stats.py         # Stats and summaries
│
├── schema.sql                  # Database schema
├── fights.yaml                 # Event and fight data
├── sources.yaml                # Analyst sources
└── README.md                   # This file
```

## 🔧 Advanced Usage

### Custom Query Optimizer

```python
from scripts.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer()

# Find fight
fight = optimizer.get_fight_by_fighters("Kape", "Royval")

# Get aggregated context (costs nothing!)
context = optimizer.aggregate_fight_context(
    fight["fight_id"],
    reveal_names=False  # Keep analyst names hidden
)

# Now you have optimized context with:
# - Pick counts
# - Top tags
# - Example rationales
# - Accuracy tiers
```

### Custom Prompt Generation

```python
from scripts.prompt_generator import PromptGenerator

generator = PromptGenerator()

prompt = generator.build_fight_analysis_prompt(
    context,
    "Why do analysts favor Kape?"
)

# prompt is lean and focused (300-500 tokens)
```

## 🎓 Marketing Message

**"ChatMMA knows who every public analyst picked. AMA!"**

### Example Responses

**Before Event (Anonymous):**
> For the main event, 15 analysts like Kape with 9 seeing it going the distance, while 5 favor Royval and 3 of them seeing a submission victory. Of the 15 analysts that like Kape, 12 are correct at least 60% of the time and our top four analysts historically all picked Kape.

**After Event (Revealed):**
> Alexander K. Lee from MMA Fighting, Drake Riggs from Yahoo Sports, and 13 other analysts picked Kape. The consensus was driven by his wrestling advantage and submission defense...

## 📊 Future Enhancements

### Planned Features
- [ ] Analyst profile pages (records, tendencies)
- [ ] Tag-based filtering ("Show me fights where wrestling was key")
- [ ] DFS optimization mode
- [ ] Web interface (currently CLI only)

### Not Needed Now
These are intentionally simple to keep the system lean:
- No ORM (raw SQL is faster)
- No web framework (CLI is sufficient)
- No complex caching (DB queries are fast enough)

## 🤝 Contributing

This is a personal project, but suggestions welcome!

## 📄 License

MIT License - Do whatever you want with this.

## 🙏 Credits

Built with:
- Claude 4 (via Anthropic API)
- SQLite (built-in Python)
- Python 3.8+

---

**Questions?** Just ask ChatMMA! 🥊
