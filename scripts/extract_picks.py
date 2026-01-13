"""
Extract fight predictions using Claude API
Handles both articles and YouTube transcripts
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from anthropic import Anthropic
from utils import load_config, load_yaml, save_json, sanitize_filename, log
import json
from datetime import datetime

def get_extraction_prompt(event_name, fights, content, source_type):
    """Generate prompt for Claude to extract predictions"""

    fight_list = "\n".join([
        f"- {fight['fighter_a']} vs {fight['fighter_b']} ({fight['weight_class']})"
        for fight in fights
    ])

    prompt = f"""You are analyzing MMA fight predictions from a {'written article' if source_type == 'article' else 'YouTube video transcript'}.

EVENT: {event_name}

FIGHTS ON THIS CARD:
{fight_list}

CONTENT TO ANALYZE:
{content[:15000]}

Extract all fight predictions from this content. For each prediction found, provide:
1. fighter_a or fighter_b (who they're picking)
2. method (KO/TKO/SUB/DEC or null if not mentioned)
3. confidence (high/medium/low based on language used)
4. reasoning (brief quote or summary of their reasoning)
5. dfs_note (any DFS/betting advice mentioned, or null)
6. extraction_confidence (0-100: your confidence this is accurate)

Return ONLY valid JSON in this exact format:
{{
  "predictions": [
    {{
      "fighter_a": "Fighter Name",
      "fighter_b": "Fighter Name",
      "pick": "fighter_a",
      "method": "KO",
      "confidence": "high",
      "reasoning": "Brief reasoning",
      "dfs_note": "Any DFS advice or null",
      "extraction_confidence": 95
    }}
  ]
}}

IMPORTANT:
- Only include fights that are EXPLICITLY predicted
- Use exact fighter names from the fight list above
- If analyst doesn't predict a fight, don't include it
- If you're unsure about a pick, lower extraction_confidence
- Return valid JSON only, no other text
"""
    return prompt

def extract_from_content(content_path, event_name, fights, source_info, api_key=None):
    """Extract predictions from article or transcript"""
    config = load_config()

    # Get API key from parameter or config
    if not api_key:
        api_key = config.get('claude_api', {}).get('key')

    if not api_key:
        raise ValueError("No API key provided")

    # Read content
    with open(content_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Initialize Claude client
    client = Anthropic(api_key=api_key)

    # Generate prompt
    prompt = get_extraction_prompt(event_name, fights, content, source_info['type'])

    log(f"Extracting predictions from {source_info['name']}")

    try:
        # Get config values with defaults
        model = config.get('claude_api', {}).get('extraction_model', 'claude-haiku-4-5-20251001')
        max_tokens = config.get('claude_api', {}).get('max_tokens', 1500)
        temperature = config.get('claude_api', {}).get('temperature', 0.3)
        cost_tracking = config.get('cost_tracking', {}).get('enabled', True)

        # Call Claude API
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Log API usage
        if cost_tracking:
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            # Haiku pricing: $0.80/MTok input, $4.00/MTok output
            cost = (input_tokens * 0.80 / 1_000_000) + (output_tokens * 4.00 / 1_000_000)
            log(f"API call: {input_tokens} in, {output_tokens} out, ${cost:.4f}")

        # Parse JSON response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                log(f"Failed to parse JSON from Claude response", "ERROR")
                return None

        # Save raw output
        raw_filename = f"{sanitize_filename(event_name)}_{sanitize_filename(source_info['name'])}_raw.json"
        raw_path = os.path.join('data', 'raw_outputs', raw_filename)
        save_json({"response": response_text, "parsed": result, "source": source_info}, raw_path)

        # Save extraction
        extract_filename = f"{sanitize_filename(event_name)}_{sanitize_filename(source_info['name'])}_extraction.json"
        extract_path = os.path.join('data', 'extractions', extract_filename)
        save_json({
            "event": event_name,
            "source": source_info,
            "extracted_at": datetime.now().isoformat(),
            "predictions": result.get('predictions', [])
        }, extract_path)

        log(f"✅ Extracted {len(result.get('predictions', []))} predictions")
        return result.get('predictions', [])

    except Exception as e:
        log(f"Error during extraction: {str(e)}", "ERROR")
        return None

def extract_all(event_name, api_key=None):
    """Extract predictions from all sources for an event"""
    sources = load_yaml('sources.yaml')['sources']
    fights_data = load_yaml('fights.yaml')

    # Find the event
    event = None
    for e in fights_data['events']:
        if e['name'] == event_name:
            event = e
            break

    if not event:
        log(f"Event {event_name} not found in fights.yaml", "ERROR")
        return

    fights = event['fights']
    log(f"Processing {len(fights)} fights for {event_name}")

    total_extracted = 0

    for source in sources:
        if source.get('event') != event_name:
            continue

        # Determine content file path
        if source['type'] == 'article':
            content_dir = 'data/articles'
        else:
            content_dir = 'data/transcripts'

        filename = f"{sanitize_filename(event_name)}_{sanitize_filename(source['name'])}.txt"
        content_path = os.path.join(content_dir, filename)

        if not os.path.exists(content_path):
            log(f"Content file not found: {content_path}", "WARNING")
            continue

        predictions = extract_from_content(content_path, event_name, fights, source, api_key)

        if predictions:
            total_extracted += len(predictions)

    log(f"Extraction complete: {total_extracted} total predictions extracted")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Extract predictions using Claude')
    parser.add_argument('event', help='Event name (e.g., "UFC 323")')
    args = parser.parse_args()

    extract_all(args.event)
