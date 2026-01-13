# ChatMMA v2.0 - Complete Workflow Example

This document shows a complete end-to-end workflow for ChatMMA v2.0.

## Scenario: Processing UFC 323

### Step 1: Initialize Database

```bash
# First time only
python scripts/init_db.py
```

Output:
```
✓ Database initialized: data/chatmma.db
✓ Tables created: events, fights, analysts, predictions, fight_summaries, event_accuracy, context_tag_dictionary
```

### Step 2: Prepare Event Data

Your `fights.yaml` should have the event:

```yaml
events:
  - name: "UFC 323"
    date: "2025-12-06"
    location: "Las Vegas, Nevada"
    fights:
      - fighter_a: "Merab Dvalishvili"
        fighter_b: "Petr Yan"
        weight_class: "Bantamweight"
        is_main_card: true
        scheduled_rounds: 5
      # ... more fights
```

### Step 3: Extract Predictions (Manual Method)

Since you're manually extracting from articles/videos, you can use the manual add script:

```bash
python scripts/add_prediction_manual.py \
  --event "UFC 323" \
  --fight "Merab Dvalishvili vs Petr Yan" \
  --analyst "Analyst_001" \
  --pick "Merab Dvalishvili" \
  --confidence "high" \
  --method "DEC" \
  --tags "merab_cardio,merab_wrestling,merab_pressure,yan_striking_defense" \
  --notes "Alexander K. Lee from MMA Fighting believes Merab's relentless pace and wrestling pressure will overwhelm Yan over 5 rounds. He notes that Yan's striking defense is excellent, but Merab's cardio advantage becomes decisive in championship rounds."
```

Output:
```
✅ Added prediction:
   Fight: Merab Dvalishvili vs Petr Yan
   Analyst: Analyst_001
   Pick: Merab Dvalishvili (high confidence)
   Tags: merab_cardio, merab_wrestling, merab_pressure, yan_striking_defense
```

**Or** use the AI extraction method:

```bash
# Step 3a: Save article content to file
# (manually copy/paste or use fetch script)

# Step 3b: Extract with AI
python scripts/extract_predictions.py \
  --event "UFC 323" \
  --content-file "data/articles/ufc_323_analyst_001.txt" \
  --fights fights.yaml
```

Output:
```
✓ Loaded 12 fights for UFC 323
📄 Extracting from: data/articles/ufc_323_analyst_001.txt
✓ Extracted 8 predictions
💰 Cost: $0.0024

  Merab Dvalishvili over Petr Yan
  Tags: merab_cardio, merab_wrestling, merab_pressure
  Notes: Alexander K. Lee from MMA Fighting believes Merab's relentless pace...

✓ Saved to: data/extractions/UFC_323_analyst_001.json
```

### Step 4: Load Predictions Into Database

```bash
python scripts/load_predictions.py --event "UFC 323"
```

Output:
```
✓ Loaded event: UFC 323 (2025-12-06)
✓ Event ID: 1
✓ Loaded 12 fights

📥 Loading 7 extraction files...

  Loading Analyst_001...
  ✓ Loaded 8 predictions

  Loading Analyst_002...
  ✓ Loaded 10 predictions

  ... (continues for all analysts)

✅ Total predictions loaded: 67
```

### Step 5: Generate Fight Summaries (Optional but Recommended)

```bash
python scripts/update_stats.py --event "UFC 323" --action summaries
```

Output:
```
📝 Generating fight summaries...
  ✓ Merab Dvalishvili vs Petr Yan: Merab Dvalishvili favored by 5 analysts, Petr Yan by 2. Key factor for Merab Dvalishvili: merab cardio.
  ✓ Alexander Volkov vs Jailton Almeida: Jailton Almeida favored by 6 analysts, Alexander Volkov by 1. Key factor for Jailton Almeida: almeida grappling.
  ... (continues for all fights)

✅ Stats updated successfully
```

### Step 6: Use the Chatbot!

```bash
python scripts/chatbot.py
```

Interactive session:
```
============================================================
ChatMMA - Ask me anything about MMA analyst predictions!
Type 'quit' or 'exit' to end the session
============================================================

🥊 You: Who will win between Merab and Yan?

⏳ Thinking...

🤖 ChatMMA: For the bantamweight title fight between Merab Dvalishvili
and Petr Yan at UFC 323, the consensus heavily favors Merab with 5 out
of 7 analysts picking him to win.

The primary factors driving this consensus are Merab's exceptional cardio
(mentioned by 4 analysts), his relentless wrestling pressure (mentioned
by 5 analysts), and his ability to maintain pace over 5 rounds. While
analysts acknowledge Yan's superior striking technique and defensive
skills, they believe Merab's pressure and volume will be overwhelming
in the championship rounds.

Most analysts expect this to go the distance, with 4 of the 5 picking
Merab via decision. The consensus view is that Yan's striking won't be
enough to offset Merab's cardio and wrestling advantages over 25 minutes.

💰 Query cost: $0.0011 (412 tokens)

🥊 You: What about Volkov vs Almeida?

⏳ Thinking...

🤖 ChatMMA: For the heavyweight bout between Alexander Volkov and
Jailton Almeida, the consensus strongly favors Almeida with 6 out of
7 analysts picking him.

Analysts highlight Almeida's dominant grappling as the key factor, with
all 6 who picked him specifically mentioning his submission threat and
ground control. The concern for Volkov is that while his striking and
reach are advantages, his takedown defense has been vulnerable against
elite grapplers.

Interestingly, 4 of the 6 analysts picking Almeida predict a finish via
submission, expecting him to get the fight to the ground and secure a
tap. The one analyst who picked Volkov cited his improved takedown
defense and the potential to keep the fight at distance.

💰 Query cost: $0.0009 (387 tokens)

🥊 You: quit

Thanks for using ChatMMA! 👊
```

### Step 7: After the Event - Update Results

Once UFC 323 happens:

```bash
# Update fight results (you can do this via SQL or a script)
sqlite3 data/chatmma.db

# Example:
UPDATE fights SET result = 'fighter_a_win', method = 'DEC_U', round = 5
WHERE event_id = 1 AND fighter_a = 'Merab Dvalishvili';

UPDATE events SET results_entered = 1 WHERE name = 'UFC 323';
```

Then update stats:

```bash
python scripts/update_stats.py --event "UFC 323" --action accuracy
```

Output:
```
📊 Updating analyst accuracy...
  Analyst_001: 6/8 (75.0%)
  Analyst_002: 7/10 (70.0%)
  Analyst_003: 5/9 (55.6%)
  Analyst_004: 8/10 (80.0%)
  Analyst_005: 4/8 (50.0%)
  Analyst_006: 6/11 (54.5%)
  Analyst_007: 7/11 (63.6%)

✅ Stats updated successfully
```

Now when users ask about future events, ChatMMA will reference historical accuracy:

```
🥊 You: Who will win Kape vs Royval?

🤖 ChatMMA: For the flyweight main event, 15 analysts favor Kape with
9 expecting it to go the distance. Of the 15 analysts picking Kape,
12 have demonstrated at least 60% accuracy historically, and our top
four most accurate analysts all picked Kape...
```

## Cost Analysis

### Traditional Approach
- Send all 67 predictions to Claude
- ~8000 tokens input + 500 tokens output
- Cost: $0.024 + $0.0075 = **$0.032 per query**

### ChatMMA v2.0 (Optimized)
- Python filters and aggregates context
- Send only relevant summary
- ~400 tokens input + 300 tokens output
- Cost: $0.0012 + $0.0045 = **$0.0057 per query**

**Savings: 82% reduction** 🎉

## Key Takeaways

1. **Context tags are powerful** - Enable intelligent filtering and aggregation
2. **Pre-filtering is crucial** - Don't send raw predictions to Claude
3. **Notes add depth** - Users want to know "why", not just "who"
4. **Anonymity matters** - Don't spoil predictions before events
5. **Historical accuracy adds credibility** - Track and reference it

---

**Questions?** See README.md or just try it out!
