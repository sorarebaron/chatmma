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

    def answer_question(self, user_question, event_name=None, reveal_names=False):
        """
        Main method to answer user questions using comprehensive context approach.

        Args:
            user_question: User's natural language question
            event_name: Optional event name to scope query
            reveal_names: Whether to reveal analyst names (True after event)

        Returns:
            dict with answer, context, and metadata
        """
        # Get full event context (all fights and predictions)
        full_context = self.optimizer.get_full_event_context(event_name)

        if not full_context:
            return {
                "answer": "Sorry, I don't have any event data available yet. Please make sure predictions have been loaded.",
                "context": None,
                "metadata": {"query_type": "no_data"}
            }

        # Build comprehensive prompt with all data
        prompt = self.generator.build_comprehensive_prompt(full_context, user_question)

        # Call Claude with full context
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text

        return {
            "answer": answer,
            "context": full_context,
            "metadata": {
                "query_type": "comprehensive",
                "event": full_context['event_name'],
                "fights_count": len(full_context['fights']),
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
