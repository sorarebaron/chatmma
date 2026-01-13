"""
ChatMMA - Interactive chat interface
Ask questions about fights, fighters, and get consensus predictions
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import sqlite3
from anthropic import Anthropic
from utils import load_config, log

def get_database_context(query_lower):
    """Fetch relevant data from database based on query"""
    config = load_config()
    conn = sqlite3.connect(config['database']['path'])
    cursor = conn.cursor()

    context = {}

    # Check if asking about a specific event
    cursor.execute('SELECT name FROM events ORDER BY date DESC LIMIT 10')
    recent_events = [row[0] for row in cursor.fetchall()]

    event_name = None
    for event in recent_events:
        if event.lower() in query_lower:
            event_name = event
            break

    if event_name:
        # Get fights for this event
        cursor.execute('''
            SELECT f.id, f.fighter_a, f.fighter_b, f.weight_class,
                   f.result, f.method
            FROM fights f
            JOIN events e ON f.event_id = e.id
            WHERE e.name = ?
        ''', (event_name,))
        fights = cursor.fetchall()

        context['event'] = event_name
        context['fights'] = []

        for fight in fights:
            fight_id, fa, fb, wc, result, method = fight

            # Get predictions for this fight
            cursor.execute('''
                SELECT s.analyst, s.accuracy_rate, p.prediction, p.method,
                       p.reasoning, p.analyst_confidence, s.type
                FROM predictions p
                JOIN sources s ON p.source_id = s.id
                WHERE p.fight_id = ? AND p.qa_status = 'approved'
            ''', (fight_id,))
            predictions = cursor.fetchall()

            context['fights'].append({
                'fighter_a': fa,
                'fighter_b': fb,
                'weight_class': wc,
                'result': result,
                'method': method,
                'predictions': predictions
            })

    # Get top analysts
    cursor.execute('''
        SELECT analyst, accuracy_rate, total_predictions, type
        FROM sources
        WHERE total_predictions > 0
        ORDER BY accuracy_rate DESC
        LIMIT 5
    ''')
    context['top_analysts'] = cursor.fetchall()

    conn.close()
    return context

def format_context(context):
    """Format database context for Claude"""
    if not context:
        return "No relevant data found in database."

    parts = []

    if 'event' in context:
        parts.append(f"EVENT: {context['event']}")
        parts.append(f"\nFIGHTS AND PREDICTIONS:")

        for fight in context['fights']:
            parts.append(f"\n{fight['fighter_a']} vs {fight['fighter_b']} ({fight['weight_class']})")

            if fight['result']:
                parts.append(f"  Actual Result: {fight['result']} by {fight['method']}")

            if fight['predictions']:
                parts.append(f"  Analyst Predictions:")
                for pred in fight['predictions']:
                    analyst, acc, pick, method, reasoning, conf, type_ = pred
                    pick_name = fight['fighter_a'] if pick == 'fighter_a' else fight['fighter_b']
                    parts.append(f"    - {analyst} ({type_}, {acc:.1f}% accurate): {pick_name}" +
                               (f" by {method}" if method else "") +
                               (f" [{conf} confidence]" if conf else ""))
                    if reasoning:
                        parts.append(f"      Reasoning: {reasoning[:200]}")

    if 'top_analysts' in context and context['top_analysts']:
        parts.append("\n\nTOP PERFORMING ANALYSTS:")
        for analyst, acc, total, type_ in context['top_analysts']:
            parts.append(f"  - {analyst} ({type_}): {acc:.1f}% accurate ({total} predictions)")

    return "\n".join(parts)

def chat(user_query):
    """Process user query and generate response"""
    config = load_config()
    client = Anthropic(api_key=config['claude_api']['key'])

    # Get relevant database context
    context = get_database_context(user_query.lower())
    formatted_context = format_context(context)

    # Build prompt
    system_prompt = """You are ChatMMA, an AI assistant that helps users understand MMA predictions by synthesizing insights from multiple expert analysts.

Your job is to:
1. Analyze predictions from multiple analysts with different accuracy records
2. Provide consensus picks weighted by analyst credibility
3. Explain reasoning and highlight any disagreements
4. Share DFS/betting insights when relevant
5. Answer questions about fighters and matchups

Be concise, accurate, and helpful. Weight predictions from more accurate analysts more heavily."""

    user_prompt = f"""USER QUESTION: {user_query}

RELEVANT DATA FROM DATABASE:
{formatted_context}

Please answer the user's question based on this data. If there's a consensus among analysts, state it clearly. If analysts disagree, explain the split and which analysts are on each side."""

    try:
        message = client.messages.create(
            model=config['claude_api']['chat_model'],
            max_tokens=2000,
            temperature=0.5,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        response = message.content[0].text

        # Log API usage
        if config['cost_tracking']['enabled']:
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            # Sonnet pricing: $3.00/MTok input, $15.00/MTok output
            cost = (input_tokens * 3.00 / 1_000_000) + (output_tokens * 15.00 / 1_000_000)
            log(f"Chat API call: {input_tokens} in, {output_tokens} out, ${cost:.4f}")

        return response

    except Exception as e:
        log(f"Error in chat: {str(e)}", "ERROR")
        return f"Error: {str(e)}"

def main():
    """Interactive chat loop"""
    print("\n" + "="*60)
    print("ChatMMA - MMA Predictions Analysis")
    print("="*60)
    print("Ask questions about fights, fighters, or predictions")
    print("Type 'quit' or 'exit' to quit\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("\nChatMMA: ", end="", flush=True)
            response = chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")

if __name__ == "__main__":
    main()
