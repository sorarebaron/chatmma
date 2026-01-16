#!/usr/bin/env python3
"""
ChatMMA - Main chatbot interface.
Usage: python scripts/chatbot.py
"""
import os
import sys
from anthropic import Anthropic
from query_optimizer import QueryOptimizer
from prompt_generator import PromptGenerator


class ChatMMA:
    """Main chatbot interface for ChatMMA."""

    def __init__(self, api_key=None, db_path="data/chatmma.db", model="claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in environment or pass to constructor.")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.optimizer = QueryOptimizer(db_path)
        self.generator = PromptGenerator()

        # Cache entities for semantic matching
        self._cache_entities()

    def _cache_entities(self):
        """Cache all fighter names, events, and fights for semantic matching."""
        import sqlite3
        conn = sqlite3.connect(self.optimizer.db_path)
        cursor = conn.cursor()

        # Cache events
        cursor.execute("SELECT id, name FROM events")
        self.events = {row[0]: row[1] for row in cursor.fetchall()}

        # Cache fights with fighter names
        cursor.execute("""
            SELECT f.id, f.fighter_a, f.fighter_b, f.event_id
            FROM fights f
        """)
        self.fights = {}
        self.fighter_to_fights = {}  # Map fighter name → list of fight IDs

        for row in cursor.fetchall():
            fight_id, fighter_a, fighter_b, event_id = row
            self.fights[fight_id] = {
                'fighter_a': fighter_a,
                'fighter_b': fighter_b,
                'event_id': event_id
            }

            # Build reverse index: fighter name → fights they're in
            for fighter in [fighter_a, fighter_b]:
                # Store full name
                if fighter not in self.fighter_to_fights:
                    self.fighter_to_fights[fighter] = []
                self.fighter_to_fights[fighter].append(fight_id)

                # Also store last name for partial matching
                last_name = fighter.split()[-1] if ' ' in fighter else fighter
                if last_name not in self.fighter_to_fights:
                    self.fighter_to_fights[last_name] = []
                self.fighter_to_fights[last_name].append(fight_id)

        conn.close()

    def detect_event_query(self, question):
        """
        Detect if question is about an event using semantic matching.
        Returns event_name or None.
        """
        question_lower = question.lower()

        # Patterns that suggest event-level query (not fight-specific)
        event_patterns = ["top picks", "consensus picks", "main card", "full card", "event predictions", "all fights"]

        # Check if any event-level pattern matches
        is_event_query = any(pattern in question_lower for pattern in event_patterns)

        if is_event_query:
            # Try to match event names semantically
            for event_id, event_name in self.events.items():
                event_name_lower = event_name.lower()

                # Check if event name appears in question
                if event_name_lower in question_lower:
                    return event_name

                # Check for partial matches (e.g., "vegas 112" matching "UFC Vegas 112")
                words = event_name_lower.split()
                if len(words) >= 2 and all(word in question_lower for word in words):
                    return event_name

            # If no specific event found but it's an event query, return the most recent event
            if self.events:
                events = self.optimizer.get_all_events()
                if events:
                    return events[0]['name']

        return None

    def detect_fight_query(self, question):
        """
        Detect if question is about a specific fight using semantic matching.
        Returns (fighter_a, fighter_b, event_name) or None.
        """
        question_lower = question.lower()

        # Find all fighter names mentioned in the question
        mentioned_fighters = []
        for fighter_name in self.fighter_to_fights.keys():
            if fighter_name.lower() in question_lower:
                mentioned_fighters.append(fighter_name)

        # If we found 2+ fighters, check if any pair shares a fight
        if len(mentioned_fighters) >= 2:
            # Try to find a fight that contains any two mentioned fighters
            for i, fighter1 in enumerate(mentioned_fighters):
                fights1 = set(self.fighter_to_fights.get(fighter1, []))

                for fighter2 in mentioned_fighters[i+1:]:
                    fights2 = set(self.fighter_to_fights.get(fighter2, []))

                    # Find common fights
                    common_fights = fights1 & fights2

                    if common_fights:
                        # Get the first common fight
                        fight_id = list(common_fights)[0]
                        fight = self.fights[fight_id]
                        event_name = self.events.get(fight['event_id'])

                        return (fight['fighter_a'], fight['fighter_b'], event_name)

        return None

    def answer_question(self, user_question, event_name=None, reveal_names=False):
        """
        Main method to answer user questions.

        Args:
            user_question: User's natural language question
            event_name: Optional event name to scope query
            reveal_names: Whether to reveal analyst names (True after event)

        Returns:
            dict with answer, context, and metadata
        """
        # Detect if question is about an event
        if not event_name:
            detected_event = self.detect_event_query(user_question)
            if detected_event:
                event_name = detected_event

        # Detect if question is about a specific fight
        fight_info = self.detect_fight_query(user_question)

        if fight_info:
            fighter_a, fighter_b, detected_event = fight_info
            event = event_name or detected_event

            # Get fight data
            fight = self.optimizer.get_fight_by_fighters(fighter_a, fighter_b, event)

            if not fight:
                return {
                    "answer": f"Sorry, I couldn't find a fight between {fighter_a} and {fighter_b}. Please check the fighter names or specify the event.",
                    "context": None,
                    "metadata": {"query_type": "fight_not_found"}
                }

            # Get aggregated context (cost-optimized!)
            context = self.optimizer.aggregate_fight_context(
                fight["fight_id"],
                reveal_names=reveal_names or fight["results_entered"]
            )

            if not context or context["summary"]["total_predictions"] == 0:
                return {
                    "answer": f"I found the fight, but don't have any analyst predictions yet for {fight['fighter_a']} vs {fight['fighter_b']}.",
                    "context": context,
                    "metadata": {"query_type": "no_predictions"}
                }

            # Generate lean prompt
            prompt = self.generator.build_fight_analysis_prompt(context, user_question)

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            answer = response.content[0].text

            return {
                "answer": answer,
                "context": context,
                "metadata": {
                    "query_type": "fight_analysis",
                    "fight": fight,
                    "prompt_length": len(prompt),
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "cost_estimate": self._estimate_cost(response.usage)
                }
            }

        # Check if it's an event-level question
        elif event_name:
            event_summary = self.optimizer.get_event_predictions_summary(event_name)

            if not event_summary:
                return {
                    "answer": f"Sorry, I don't have predictions for {event_name} yet.",
                    "context": None,
                    "metadata": {"query_type": "event_not_found"}
                }

            prompt = self.generator.build_event_summary_prompt(event_summary, user_question)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            answer = response.content[0].text

            return {
                "answer": answer,
                "context": event_summary,
                "metadata": {
                    "query_type": "event_summary",
                    "prompt_length": len(prompt),
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "cost_estimate": self._estimate_cost(response.usage)
                }
            }

        # General question - provide lightweight context as fallback
        else:
            # Get minimal context about available data
            lightweight_context = self.optimizer.get_lightweight_context()

            prompt = self.generator.build_general_prompt(user_question, lightweight_context)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )

            answer = response.content[0].text

            return {
                "answer": answer,
                "context": lightweight_context,
                "metadata": {
                    "query_type": "general_with_context",
                    "prompt_length": len(prompt),
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "cost_estimate": self._estimate_cost(response.usage)
                }
            }

    def _estimate_cost(self, usage):
        """Estimate cost based on token usage."""
        # Claude Sonnet 4 pricing (as of 2026)
        input_cost_per_1k = 0.003  # $3 per million tokens
        output_cost_per_1k = 0.015  # $15 per million tokens

        input_cost = (usage.input_tokens / 1000) * input_cost_per_1k
        output_cost = (usage.output_tokens / 1000) * output_cost_per_1k

        return {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.input_tokens + usage.output_tokens,
            "cost_usd": round(input_cost + output_cost, 4)
        }

    def interactive_mode(self):
        """Run chatbot in interactive CLI mode."""
        print("=" * 60)
        print("ChatMMA - Ask me anything about MMA analyst predictions!")
        print("Type 'quit' or 'exit' to end the session")
        print("=" * 60)
        print()

        while True:
            try:
                question = input("\n🥊 You: ").strip()

                if question.lower() in ['quit', 'exit', 'q']:
                    print("\nThanks for using ChatMMA! 👊")
                    break

                if not question:
                    continue

                print("\n⏳ Thinking...\n")

                result = self.answer_question(question)

                print(f"🤖 ChatMMA: {result['answer']}\n")

                # Show metadata
                if result['metadata'].get('cost_estimate'):
                    cost = result['metadata']['cost_estimate']
                    print(f"💰 Query cost: ${cost['cost_usd']} ({cost['total_tokens']} tokens)")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👊")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again or type 'quit' to exit.\n")


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        # Non-interactive mode: answer single question
        question = " ".join(sys.argv[1:])
        chatbot = ChatMMA()
        result = chatbot.answer_question(question)
        print(result['answer'])
    else:
        # Interactive mode
        chatbot = ChatMMA()
        chatbot.interactive_mode()


if __name__ == "__main__":
    main()
