#!/usr/bin/env python3
"""
Prompt generator for cost-efficient Claude queries.
Builds lean, focused prompts using pre-filtered context.
"""


class PromptGenerator:
    """Generates optimized prompts for ChatMMA queries."""

    @staticmethod
    def build_fight_analysis_prompt(context, user_question):
        """
        Build prompt for fight analysis questions.

        Args:
            context: Aggregated context from QueryOptimizer
            user_question: User's natural language question

        Returns:
            Optimized prompt string
        """
        fight = context["fight"]
        summary = context["summary"]
        a_context = context["fighter_a_context"]
        b_context = context["fighter_b_context"]
        analyst_info = context.get("analyst_info", {})

        # Build compact prompt
        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

FIGHT CONTEXT:
Event: {fight['event']}
Fight: {fight['fighter_a']} vs {fight['fighter_b']}

PREDICTION SUMMARY:
- Total analysts: {summary['total_predictions']}
- Picking {fight['fighter_a']}: {summary['picks_for_a']} analysts
- Picking {fight['fighter_b']}: {summary['picks_for_b']} analysts
"""

        # Add fighter A context
        if a_context['top_tags']:
            prompt += f"\nKEY FACTORS FOR {fight['fighter_a'].upper()}:\n"
            for tag_data in a_context['top_tags'][:5]:
                prompt += f"- {tag_data['tag'].replace('_', ' ')}: mentioned by {tag_data['count']} analysts\n"

        if a_context['methods']:
            methods_str = ", ".join([f"{method} ({count})" for method, count in a_context['methods'].items()])
            prompt += f"Expected methods: {methods_str}\n"

        if a_context['example_rationales']:
            prompt += f"\nExample analyst reasoning for {fight['fighter_a']}:\n"
            for i, note in enumerate(a_context['example_rationales'][:2], 1):
                prompt += f"{i}. {note[:200]}...\n"

        # Add fighter B context
        if b_context['top_tags']:
            prompt += f"\nKEY FACTORS FOR {fight['fighter_b'].upper()}:\n"
            for tag_data in b_context['top_tags'][:5]:
                prompt += f"- {tag_data['tag'].replace('_', ' ')}: mentioned by {tag_data['count']} analysts\n"

        if b_context['methods']:
            methods_str = ", ".join([f"{method} ({count})" for method, count in b_context['methods'].items()])
            prompt += f"Expected methods: {methods_str}\n"

        if b_context['example_rationales']:
            prompt += f"\nExample analyst reasoning for {fight['fighter_b']}:\n"
            for i, note in enumerate(b_context['example_rationales'][:2], 1):
                prompt += f"{i}. {note[:200]}...\n"

        # Add accuracy info only if available (results must be entered first)
        a_high_acc = analyst_info.get('fighter_a_high_accuracy_count', 0)
        b_high_acc = analyst_info.get('fighter_b_high_accuracy_count', 0)

        if a_high_acc > 0 or b_high_acc > 0:
            if not analyst_info.get('reveal_names', False):
                prompt += f"\nANALYST ACCURACY (ANONYMOUS):\n"
                if a_high_acc > 0:
                    prompt += f"- {a_high_acc} analysts with 60%+ accuracy picked {fight['fighter_a']}\n"
                if b_high_acc > 0:
                    prompt += f"- {b_high_acc} analysts with 60%+ accuracy picked {fight['fighter_b']}\n"
            else:
                prompt += f"\nTOP ANALYSTS:\n"
                if analyst_info.get('top_analysts_a'):
                    prompt += f"For {fight['fighter_a']}: {', '.join(analyst_info.get('top_analysts_a', [])[:3])}\n"
                if analyst_info.get('top_analysts_b'):
                    prompt += f"For {fight['fighter_b']}: {', '.join(analyst_info.get('top_analysts_b', [])[:3])}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question based on the consensus and reasoning above
2. Focus on WHY analysts favor each fighter, not just the numbers
3. Mention specific context tags and analyst reasoning
4. If asked about methods, reference the expected finish types
5. Keep response conversational and insightful (2-4 paragraphs)
6. If results haven't been entered, don't reveal analyst names
7. Use the marketing message: "ChatMMA knows who every public analyst picked. AMA!"

RESPONSE:
"""
        return prompt

    @staticmethod
    def build_event_summary_prompt(event_summary, user_question):
        """
        Build prompt for event-level questions.
        """
        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

EVENT: {event_summary['event']} ({event_summary['date']})
Total fights tracked: {len(event_summary['fight_summaries'])}

FIGHT PREDICTIONS SUMMARY:
"""
        for fight_context in event_summary['fight_summaries']:
            fight = fight_context['fight']
            summary = fight_context['summary']
            prompt += f"\n{fight['fighter_a']} vs {fight['fighter_b']}\n"
            prompt += f"  Consensus: {summary['picks_for_a']} - {summary['picks_for_b']}\n"

            # Add top tags
            a_tags = fight_context['fighter_a_context']['top_tags'][:2]
            b_tags = fight_context['fighter_b_context']['top_tags'][:2]

            if a_tags:
                tag_str = ", ".join([t['tag'].replace('_', ' ') for t in a_tags])
                prompt += f"  {fight['fighter_a']}: {tag_str}\n"

            if b_tags:
                tag_str = ", ".join([t['tag'].replace('_', ' ') for t in b_tags])
                prompt += f"  {fight['fighter_b']}: {tag_str}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question about this event
2. Provide insights based on consensus and key factors
3. Highlight interesting patterns or contrarian picks
4. Keep response concise and actionable

RESPONSE:
"""
        return prompt

    @staticmethod
    def build_general_prompt(user_question, lightweight_context=None):
        """
        Build prompt for general questions with optional lightweight context.

        Args:
            user_question: User's question
            lightweight_context: Optional dict with available events/fights
        """
        prompt = f"""You are ChatMMA, an AI assistant that knows MMA analyst predictions.

USER QUESTION: {user_question}
"""

        if lightweight_context:
            prompt += "\nAVAILABLE DATA:\n"
            for event_name, event_data in lightweight_context.items():
                prompt += f"\n{event_name} ({event_data['date']}):\n"
                for fight in event_data['fights']:
                    prompt += f"  - {fight}\n"

            prompt += """
INSTRUCTIONS:
1. Check if the user's question is about any of the fights or events listed above
2. If YES: Tell them you have analyst predictions for that fight/event and ask them to rephrase more specifically (e.g., "Who will win X vs Y?")
3. If NO: Provide a helpful general response and let them know they can ask about any of the available fights

Use the tagline: "ChatMMA knows who every public analyst picked. AMA!"

RESPONSE:
"""
        else:
            prompt += """
This appears to be a general question. Respond helpfully and direct them to ask about specific fights or events if appropriate.

Use the marketing message: "ChatMMA knows who every public analyst picked. AMA!"

RESPONSE:
"""

        return prompt

    @staticmethod
    def build_comprehensive_prompt(full_context, user_question):
        """
        Build prompt with full event context (for events with <50 fights).

        Args:
            full_context: Dict with event info and all fights/predictions
            user_question: User's natural language question

        Returns:
            Comprehensive prompt with all data
        """
        event = full_context

        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

EVENT: {event['event_name']} - {event['event_date']}
Location: {event['event_location']}
Total Fights: {len(event['fights'])}

"""

        # Add all fights with predictions
        for fight in event['fights']:
            prompt += f"\n{'='*60}\n"
            prompt += f"FIGHT: {fight['fighter_a']} vs {fight['fighter_b']}\n"
            prompt += f"Weight Class: {fight['weight_class']}\n"
            prompt += f"Consensus: {fight['picks_for_a']} analysts pick {fight['fighter_a']}, {fight['picks_for_b']} pick {fight['fighter_b']}\n"

            if fight['predictions']:
                prompt += f"\nANALYST PREDICTIONS:\n"
                for pred in fight['predictions']:
                    pick_name = fight['fighter_a'] if pred['pick'] == 'fighter_a' else fight['fighter_b']
                    prompt += f"- {pred['analyst']}: {pick_name}\n"
                    if pred['notes']:
                        # Truncate very long notes
                        notes = pred['notes'][:150] + "..." if len(pred['notes']) > 150 else pred['notes']
                        prompt += f"  Reasoning: {notes}\n"

        prompt += f"\n{'='*60}\n"
        prompt += """
INSTRUCTIONS:
1. Answer the user's question based on the predictions above
2. If asked about a specific fight, provide detailed consensus and reasoning
3. If asked about the whole event/card, summarize top picks across all fights
4. If asked "why" analysts favor someone, explain the reasoning from their notes
5. Focus on analyst consensus and key reasoning patterns
6. Keep responses conversational and insightful (2-4 paragraphs)
7. Always end with: "ChatMMA knows who every public analyst picked. AMA!"

RESPONSE:
"""
        return prompt


# Example usage
if __name__ == "__main__":
    from query_optimizer import QueryOptimizer

    optimizer = QueryOptimizer()
    generator = PromptGenerator()

    # Test fight analysis prompt
    fight = optimizer.get_fight_by_fighters("Kape", "Royval")
    if fight:
        context = optimizer.aggregate_fight_context(fight["fight_id"])
        prompt = generator.build_fight_analysis_prompt(
            context,
            "Why do analysts favor Kape over Royval?"
        )
        print(prompt)
        print(f"\nPrompt length: {len(prompt)} characters")
