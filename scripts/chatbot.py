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

    def detect_query_type(self, question):
        """
        Detect the type of question being asked.
        Returns (query_type, details) tuple.

        Query types:
        - 'fight_specific': Question about a specific fight (fighter_a vs fighter_b)
        - 'inside_distance': Which fighters will win inside the distance
        - 'consensus_picks': Top consensus picks for an event
        - 'underdogs': Best underdog picks for an event
        - 'general': General question
        """
        question_lower = question.lower()

        # Detect inside distance questions
        inside_distance_keywords = [
            'inside the distance', 'inside distance', 'finish', 'knockout', 'ko', 'submission',
            'most likely to finish', 'end inside', 'not go the distance'
        ]
        if any(keyword in question_lower for keyword in inside_distance_keywords):
            # Extract event name if present
            event_name = self._extract_event_name(question_lower)
            return ('inside_distance', {'event_name': event_name})

        # Detect consensus picks questions
        consensus_keywords = [
            'consensus', 'top picks', 'favorites', 'who should win',
            'most likely to win', 'best bets', 'safest picks', 'locks'
        ]
        if any(keyword in question_lower for keyword in consensus_keywords):
            event_name = self._extract_event_name(question_lower)
            return ('consensus_picks', {'event_name': event_name})

        # Detect underdog questions
        underdog_keywords = [
            'underdog', 'upset', 'dark horse', 'value pick', 'sleeper',
            'best underdog', 'undervalued', 'contrarian'
        ]
        if any(keyword in question_lower for keyword in underdog_keywords):
            event_name = self._extract_event_name(question_lower)
            return ('underdogs', {'event_name': event_name})

        # Detect fight-specific questions
        vs_patterns = [" vs ", " versus ", " v ", " against "]
        for pattern in vs_patterns:
            if pattern in question_lower:
                parts = question_lower.split(pattern)
                if len(parts) == 2:
                    fighter_a = parts[0].strip().split()[-1]  # Last word before "vs"
                    fighter_b = parts[1].strip().split()[0]   # First word after "vs"
                    return ('fight_specific', {
                        'fighter_a': fighter_a.title(),
                        'fighter_b': fighter_b.title(),
                        'event_name': None
                    })

        # Check if question mentions a specific fighter (for "why do analysts favor X" type questions)
        # This is already handled by fight_specific, but we can enhance it

        return ('general', {})

    def _extract_event_name(self, question_lower):
        """Extract event name from question if present."""
        # Common event patterns
        import re

        # UFC XXX pattern
        ufc_match = re.search(r'ufc\s+(\d+|vegas\s+\d+|fight\s+night\s+\d+)', question_lower)
        if ufc_match:
            return f"UFC {ufc_match.group(1)}".title()

        # Try to get the most recent event from database if not specified
        conn = self.optimizer._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM events ORDER BY date DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

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
        # Detect query type
        query_type, details = self.detect_query_type(user_question)

        # Route to appropriate handler
        if query_type == 'fight_specific':
            return self._handle_fight_specific(user_question, details, event_name, reveal_names)
        elif query_type == 'inside_distance':
            return self._handle_inside_distance(user_question, details)
        elif query_type == 'consensus_picks':
            return self._handle_consensus_picks(user_question, details)
        elif query_type == 'underdogs':
            return self._handle_underdogs(user_question, details)
        else:
            return self._handle_general(user_question)

    def _handle_fight_specific(self, user_question, details, event_name=None, reveal_names=False):
        """Handle fight-specific questions (Q1 and Q2)."""
        fighter_a = details['fighter_a']
        fighter_b = details['fighter_b']
        event = event_name or details.get('event_name')

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

    def _handle_inside_distance(self, user_question, details):
        """Handle inside distance questions (Q3)."""
        event_name = details['event_name']

        if not event_name:
            return {
                "answer": "Please specify an event name (e.g., 'UFC Vegas 112') to get inside distance predictions.",
                "context": None,
                "metadata": {"query_type": "missing_event"}
            }

        # Get inside distance picks
        context = self.optimizer.get_inside_distance_picks(event_name)

        if not context:
            return {
                "answer": f"Sorry, I don't have predictions for {event_name} yet.",
                "context": None,
                "metadata": {"query_type": "event_not_found"}
            }

        if not context['inside_distance_picks']:
            return {
                "answer": f"I found {event_name}, but there are no strong finish predictions for this event. Most fights are expected to go the distance.",
                "context": context,
                "metadata": {"query_type": "no_finish_predictions"}
            }

        # Generate prompt
        prompt = self.generator.build_inside_distance_prompt(context, user_question)

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
                "query_type": "inside_distance",
                "event": event_name,
                "prompt_length": len(prompt),
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "cost_estimate": self._estimate_cost(response.usage)
            }
        }

    def _handle_consensus_picks(self, user_question, details):
        """Handle consensus picks questions (Q4)."""
        event_name = details['event_name']

        if not event_name:
            return {
                "answer": "Please specify an event name (e.g., 'UFC Vegas 112') to get consensus picks.",
                "context": None,
                "metadata": {"query_type": "missing_event"}
            }

        # Get consensus picks
        context = self.optimizer.get_event_consensus_picks(event_name)

        if not context:
            return {
                "answer": f"Sorry, I don't have predictions for {event_name} yet.",
                "context": None,
                "metadata": {"query_type": "event_not_found"}
            }

        if not context['consensus_picks']:
            return {
                "answer": f"I found {event_name}, but don't have enough predictions yet to determine consensus picks.",
                "context": context,
                "metadata": {"query_type": "no_consensus"}
            }

        # Generate prompt
        prompt = self.generator.build_consensus_picks_prompt(context, user_question)

        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text

        return {
            "answer": answer,
            "context": context,
            "metadata": {
                "query_type": "consensus_picks",
                "event": event_name,
                "prompt_length": len(prompt),
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "cost_estimate": self._estimate_cost(response.usage)
            }
        }

    def _handle_underdogs(self, user_question, details):
        """Handle underdog picks questions (Q5)."""
        event_name = details['event_name']

        if not event_name:
            return {
                "answer": "Please specify an event name (e.g., 'UFC Vegas 112') to get underdog picks.",
                "context": None,
                "metadata": {"query_type": "missing_event"}
            }

        # Get underdog picks
        context = self.optimizer.get_event_underdogs(event_name)

        if not context:
            return {
                "answer": f"Sorry, I don't have predictions for {event_name} yet.",
                "context": None,
                "metadata": {"query_type": "event_not_found"}
            }

        if not context['underdog_picks']:
            return {
                "answer": f"I found {event_name}, but there are no clear underdog opportunities. The consensus is strong on all fights.",
                "context": context,
                "metadata": {"query_type": "no_underdogs"}
            }

        # Generate prompt
        prompt = self.generator.build_underdogs_prompt(context, user_question)

        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text

        return {
            "answer": answer,
            "context": context,
            "metadata": {
                "query_type": "underdogs",
                "event": event_name,
                "prompt_length": len(prompt),
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "cost_estimate": self._estimate_cost(response.usage)
            }
        }

    def _handle_general(self, user_question):
        """Handle general questions."""
        prompt = self.generator.build_general_prompt(user_question)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text

        return {
            "answer": answer,
            "context": None,
            "metadata": {
                "query_type": "general",
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
