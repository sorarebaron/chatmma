#!/usr/bin/env python3
"""
Extract predictions from articles and YouTube transcripts with context tags and notes.
This version extracts structured predictions WITH reasoning.

Usage:
    python scripts/extract_predictions.py --event "UFC 323" --source sources.yaml
"""
import os
import json
import argparse
from anthropic import Anthropic


EXTRACTION_PROMPT_TEMPLATE = """You are an expert at extracting MMA fight predictions from analyst content.

Extract predictions from the following content for {event_name}.

CONTENT:
{content}

FIGHT CARD:
{fight_card}

EXTRACTION INSTRUCTIONS:
For each fight prediction you find, extract:
1. fighter_pick: Which fighter the analyst picked (use exact names from fight card)
2. confidence: "high", "medium", or "low" (infer from language)
3. method: "KO", "SUB", "DEC", "FINISH", or null if not mentioned
4. context_tags: Array of short tags describing key factors (max 5 tags per prediction)
   Examples: ["kape_wrestling_advantage", "kape_sub_defense", "royval_off_back", "cardio_concerns"]
5. notes: 2-4 sentences capturing the analyst's full reasoning in natural language

CONTEXT TAG GUIDELINES:
- Use snake_case format
- Be specific but concise
- Include fighter name when relevant
- Common categories: wrestling, striking, cardio, grappling, power, experience, stylistic_advantage
- Examples:
  * "jones_reach_advantage"
  * "ngannou_knockout_power"
  * "holloway_cardio"
  * "oliveira_submission_threat"
  * "stylistic_mismatch_favors_X"

Return your response as a JSON array:
[
  {
    "fighter_a": "Fighter A Name",
    "fighter_b": "Fighter B Name",
    "pick": "Fighter A Name",
    "confidence": "high",
    "method": "DEC",
    "context_tags": ["tag1", "tag2", "tag3"],
    "notes": "Full reasoning here in 2-4 sentences explaining why the analyst picked this fighter."
  }
]

IMPORTANT:
- Only extract explicit predictions (where analyst clearly picks a winner)
- Use exact fighter names from the fight card
- If no prediction found for a fight, don't include it
- Keep notes concise but capture the "why"
- Context tags should be factual descriptors, not opinions

JSON OUTPUT:
"""


class PredictionExtractor:
    """Extracts predictions with context tags and reasoning."""

    def __init__(self, api_key=None, model="claude-haiku-4-5-20251001"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model

    def extract_from_content(self, content, event_name, fight_card):
        """
        Extract predictions from article or transcript content.

        Args:
            content: Raw text content
            event_name: Event name (e.g., "UFC 323")
            fight_card: List of dicts with fighter_a and fighter_b

        Returns:
            List of prediction dicts with context_tags and notes
        """
        # Build fight card string
        fight_card_str = ""
        for i, fight in enumerate(fight_card, 1):
            fight_card_str += f"{i}. {fight['fighter_a']} vs {fight['fighter_b']}\n"

        # Build prompt
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            event_name=event_name,
            content=content[:30000],  # Limit content length
            fight_card=fight_card_str
        )

        # Call Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            predictions = json.loads(response_text)

            # Add metadata
            for pred in predictions:
                pred["extraction_confidence"] = 90  # High confidence for structured extraction
                pred["raw_response"] = response_text

            return {
                "predictions": predictions,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "cost": self._estimate_cost(response.usage)
            }

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response: {response_text[:500]}")
            return {"predictions": [], "error": str(e)}

        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {"predictions": [], "error": str(e)}

    def _estimate_cost(self, usage):
        """Estimate cost for Haiku."""
        # Claude Haiku pricing
        input_cost = (usage.input_tokens / 1000000) * 0.80
        output_cost = (usage.output_tokens / 1000000) * 4.00
        return round(input_cost + output_cost, 4)

    def save_extraction(self, predictions, output_path):
        """Save extracted predictions to JSON."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(predictions, f, indent=2)


def load_fight_card(yaml_path, event_name):
    """Load fight card from fights.yaml."""
    import yaml
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    for event in data.get('events', []):
        if event['name'] == event_name:
            return event['fights']

    return []


def main():
    parser = argparse.ArgumentParser(description="Extract predictions with context tags")
    parser.add_argument("--event", required=True, help="Event name")
    parser.add_argument("--source", default="sources.yaml", help="Sources YAML")
    parser.add_argument("--fights", default="fights.yaml", help="Fights YAML")
    parser.add_argument("--content-file", help="Content file to extract from")
    args = parser.parse_args()

    # Load fight card
    fight_card = load_fight_card(args.fights, args.event)
    if not fight_card:
        print(f"❌ No fights found for {args.event}")
        return

    print(f"✓ Loaded {len(fight_card)} fights for {args.event}")

    # Initialize extractor
    extractor = PredictionExtractor()

    # Read content file
    if args.content_file:
        with open(args.content_file, 'r') as f:
            content = f.read()

        print(f"📄 Extracting from: {args.content_file}")
        result = extractor.extract_from_content(content, args.event, fight_card)

        if result['predictions']:
            print(f"✓ Extracted {len(result['predictions'])} predictions")
            print(f"💰 Cost: ${result['cost']}")

            # Show sample
            for pred in result['predictions'][:2]:
                print(f"\n  {pred['pick']} over {pred['fighter_a'] if pred['pick'] != pred['fighter_a'] else pred['fighter_b']}")
                print(f"  Tags: {', '.join(pred['context_tags'][:3])}")
                print(f"  Notes: {pred['notes'][:100]}...")

            # Save
            output_path = f"data/extractions/{args.event}_{os.path.basename(args.content_file)}.json"
            extractor.save_extraction(result['predictions'], output_path)
            print(f"\n✓ Saved to: {output_path}")
        else:
            print(f"⚠️  No predictions found")


if __name__ == "__main__":
    main()
