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

        # Add accuracy info (but maintain anonymity if needed)
        if not analyst_info.get('reveal_names', False):
            prompt += f"\nANALYST ACCURACY (ANONYMOUS):\n"
            prompt += f"- {analyst_info.get('fighter_a_high_accuracy_count', 0)} analysts with 60%+ accuracy picked {fight['fighter_a']}\n"
            prompt += f"- {analyst_info.get('fighter_b_high_accuracy_count', 0)} analysts with 60%+ accuracy picked {fight['fighter_b']}\n"
        else:
            prompt += f"\nTOP ANALYSTS:\n"
            prompt += f"For {fight['fighter_a']}: {', '.join(analyst_info.get('top_analysts_a', [])[:3])}\n"
            prompt += f"For {fight['fighter_b']}: {', '.join(analyst_info.get('top_analysts_b', [])[:3])}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question based on the consensus and reasoning above
2. Focus on WHY analysts favor each fighter, not just the numbers
3. Mention specific context tags and analyst reasoning
4. If asked about methods, reference the expected finish types
5. Keep response conversational and insightful (2-4 paragraphs)
6. If results haven't been entered, don't reveal analyst names

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
    def build_inside_distance_prompt(context, user_question):
        """
        Build prompt for inside distance questions.
        """
        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

EVENT: {context['event']}

FIGHTERS MOST LIKELY TO WIN INSIDE THE DISTANCE (KO/TKO/SUB):
"""

        if not context['inside_distance_picks']:
            prompt += "\nNo fighters have significant finish predictions for this event.\n"
        else:
            for idx, pick in enumerate(context['inside_distance_picks'][:10], 1):
                prompt += f"\n{idx}. {pick['favored_fighter']} ({pick['fight']})\n"
                prompt += f"   - {pick['finish_prediction_count']} analysts predict finish\n"

                # List methods
                methods = [m['method'] for m in pick['methods']]
                method_counts = {}
                for m in methods:
                    method_counts[m] = method_counts.get(m, 0) + 1
                prompt += f"   - Methods: {', '.join([f'{m} ({c})' for m, c in method_counts.items()])}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question about which fighters are most likely to win inside the distance
2. Focus on the fighters with the most finish predictions
3. Mention the expected methods (KO, TKO, SUB)
4. Keep response conversational and actionable (2-3 paragraphs)

RESPONSE:
"""
        return prompt

    @staticmethod
    def build_consensus_picks_prompt(context, user_question):
        """
        Build prompt for consensus picks questions.
        """
        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

EVENT: {context['event']}

CONSENSUS PICKS (sorted by strength):
"""

        for idx, pick in enumerate(context['consensus_picks'], 1):
            prompt += f"\n{idx}. {pick['consensus_fighter']} over {pick['fighter_a'] if pick['consensus_fighter'] == pick['fighter_b'] else pick['fighter_b']}\n"
            prompt += f"   - Consensus: {pick['consensus_count']}-{pick['opposing_count']} ({pick['consensus_percentage']:.0f}%)\n"
            prompt += f"   - High accuracy analysts: {pick['high_accuracy_count']}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question about consensus picks
2. Focus on the strongest consensus picks (highest percentages)
3. Mention which picks have the most high-accuracy analyst support
4. Keep response conversational and actionable (2-3 paragraphs)

RESPONSE:
"""
        return prompt

    @staticmethod
    def build_underdogs_prompt(context, user_question):
        """
        Build prompt for underdog picks questions.
        """
        prompt = f"""You are ChatMMA, an AI that synthesizes MMA analyst predictions.

USER QUESTION: {user_question}

EVENT: {context['event']}

BEST UNDERDOG PICKS (sorted by value):
"""

        if not context['underdog_picks']:
            prompt += "\nNo clear underdog opportunities identified for this event.\n"
        else:
            for idx, pick in enumerate(context['underdog_picks'][:8], 1):
                prompt += f"\n{idx}. {pick['underdog']} ({pick['fight']})\n"
                prompt += f"   - Underdog pick: {pick['underdog_count']}-{pick['favorite_count']} ({pick['underdog_percentage']:.0f}%)\n"
                prompt += f"   - High accuracy analysts supporting: {len(pick['high_accuracy_analysts'])}\n"

                if pick['top_tags']:
                    tags_str = ', '.join([t['tag'].replace('_', ' ') for t in pick['top_tags']])
                    prompt += f"   - Key factors: {tags_str}\n"

                if pick['high_accuracy_analysts']:
                    analyst_names = [a['name'] for a in pick['high_accuracy_analysts'][:2]]
                    prompt += f"   - Backed by: {', '.join(analyst_names)}\n"

        prompt += """
INSTRUCTIONS:
1. Answer the user's question about underdog picks
2. Focus on underdogs with high-accuracy analyst support (value picks)
3. Explain why these underdogs have potential despite being less popular
4. Keep response conversational and actionable (2-3 paragraphs)

RESPONSE:
"""
        return prompt

    @staticmethod
    def build_general_prompt(user_question):
        """
        Build prompt for general questions not tied to specific fights.
        """
        prompt = f"""You are ChatMMA, an AI assistant for MMA predictions.

The user asked: {user_question}

This appears to be a general question. Respond helpfully and direct them to ask about specific fights or events if appropriate.

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
