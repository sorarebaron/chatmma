#!/usr/bin/env python3
"""Test the Silva name fix."""
import sys
sys.path.insert(0, 'scripts')

from query_optimizer import QueryOptimizer

print("=" * 70)
print("TESTING SILVA NAME FIX")
print("=" * 70)

optimizer = QueryOptimizer()

# Test 1: Full name extraction (simulated from chatbot)
question = "who will win the Jean Silva vs Arnold Allen fight at UFC 324?"
print(f"\nQuestion: {question}")

# Simulate the new extraction logic
question_lower = question.lower()
parts = question_lower.split(" vs ")
if len(parts) == 2:
    left_words = parts[0].strip().split()
    fighter_a_words = left_words[-2:] if len(left_words) >= 2 else left_words[-1:]
    fighter_a = ' '.join(fighter_a_words).title()

    right_words = parts[1].strip().split()
    fighter_b_words = right_words[:2] if len(right_words) >= 2 else right_words[:1]
    fighter_b = ' '.join(fighter_b_words).title()

    print(f"Extracted fighter_a: '{fighter_a}'")
    print(f"Extracted fighter_b: '{fighter_b}'")

# Test 2: Database lookup
print(f"\n--- Testing database lookup ---")
fight = optimizer.get_fight_by_fighters("Jean Silva", "Arnold Allen", "UFC 324")

if fight:
    print(f"✅ CORRECT! Found: {fight['fighter_a']} vs {fight['fighter_b']}")
    print(f"   Event: {fight['event']}")
else:
    print(f"❌ FAILED! Could not find Jean Silva vs Arnold Allen")

# Test 3: Make sure Natalia Silva fight still works
print(f"\n--- Testing Natalia Silva fight ---")
fight2 = optimizer.get_fight_by_fighters("Natalia Silva", "Rose Namajunas", "UFC 324")

if fight2:
    print(f"✅ CORRECT! Found: {fight2['fighter_a']} vs {fight2['fighter_b']}")
else:
    print(f"❌ FAILED! Could not find Natalia Silva vs Rose Namajunas")

# Test 4: Make sure wrong match doesn't happen
print(f"\n--- Testing that Silva + Arnold doesn't match Natalia Silva ---")
fight3 = optimizer.get_fight_by_fighters("Silva", "Arnold", "UFC 324")

if fight3:
    print(f"Found: {fight3['fighter_a']} vs {fight3['fighter_b']}")
    if "Jean Silva" in fight3['fighter_a'] or "Jean Silva" in fight3['fighter_b']:
        print(f"✅ CORRECT! Matched Jean Silva (not Natalia)")
    else:
        print(f"❌ WRONG! Matched {fight3['fighter_a']} vs {fight3['fighter_b']}")
else:
    print(f"❌ No match found")

print("\n" + "=" * 70)
