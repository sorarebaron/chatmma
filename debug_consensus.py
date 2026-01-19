#!/usr/bin/env python3
"""
Debug script to trace the exact flow of a consensus query.
"""
import sys
sys.path.insert(0, 'scripts')

from query_optimizer import QueryOptimizer
import re

def debug_query(question):
    print("=" * 70)
    print("DEBUG: CONSENSUS PICKS QUERY")
    print("=" * 70)
    print(f"\nOriginal question: {question}")

    # Step 1: Lowercase
    question_lower = question.lower()
    print(f"Lowercase: {question_lower}")

    # Step 2: Check for consensus keywords
    consensus_keywords = [
        'consensus', 'top picks', 'favorites', 'who should win',
        'most likely to win', 'best bets', 'safest picks', 'locks'
    ]
    print(f"\nChecking for consensus keywords...")
    for kw in consensus_keywords:
        if kw in question_lower:
            print(f"  ✅ Found: '{kw}'")
            break
    else:
        print(f"  ❌ No consensus keywords found")
        return

    # Step 3: Extract event name
    print(f"\nExtracting event name...")
    ufc_match = re.search(r'ufc\s+(\d+|vegas\s+\d+|fight\s+night\s+\d+)', question_lower)
    if ufc_match:
        captured = ufc_match.group(1)
        event_name = f"UFC {captured.title()}"
        print(f"  Regex matched: '{captured}'")
        print(f"  Event name: '{event_name}'")
    else:
        print(f"  ❌ No UFC pattern matched")
        return

    # Step 4: Query database
    print(f"\nQuerying database...")
    optimizer = QueryOptimizer()

    # First check if event exists
    import sqlite3
    conn = sqlite3.connect('data/chatmma.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM events WHERE name = ?", (event_name,))
    result = cursor.fetchone()

    if result:
        print(f"  ✅ Event found in database: '{result[0]}'")
    else:
        print(f"  ❌ Event NOT found in database")
        print(f"\n  Available events:")
        cursor.execute("SELECT name FROM events")
        for row in cursor.fetchall():
            print(f"    - {row[0]}")
        conn.close()
        return
    conn.close()

    # Now try get_event_consensus_picks
    print(f"\nCalling get_event_consensus_picks('{event_name}')...")
    result = optimizer.get_event_consensus_picks(event_name)

    if result:
        print(f"  ✅ SUCCESS!")
        print(f"  Event: {result['event']}")
        print(f"  Consensus picks: {len(result['consensus_picks'])}")
        print(f"\n  Top 5 picks:")
        for i, pick in enumerate(result['consensus_picks'][:5], 1):
            print(f"    {i}. {pick['consensus_fighter']}: {pick['consensus_count']}-{pick['opposing_count']} ({pick['consensus_percentage']:.0f}%)")
    else:
        print(f"  ❌ FAILED - returned None")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    debug_query("who are the top picks for UFC Vegas 112?")
