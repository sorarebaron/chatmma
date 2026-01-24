#!/usr/bin/env python3
"""Test the improved name extraction logic."""

def extract_fighter_names(question):
    """Extract fighter names from question."""
    question_lower = question.lower()

    vs_patterns = [" vs ", " vs. ", " versus ", " v ", " against "]
    for pattern in vs_patterns:
        if pattern in question_lower:
            parts = question_lower.split(pattern)
            if len(parts) == 2:
                # Extract up to 2 words before "vs" for full names
                left_words = parts[0].strip().split()
                fighter_a_words = left_words[-2:] if len(left_words) >= 2 else left_words[-1:]
                fighter_a = ' '.join(fighter_a_words).title()

                # Extract up to 2 words after "vs" for full names
                right_words = parts[1].strip().split()
                fighter_b_words = right_words[:2] if len(right_words) >= 2 else right_words[:1]
                fighter_b = ' '.join(fighter_b_words).title()

                return fighter_a, fighter_b
    return None, None

print("=" * 70)
print("TESTING IMPROVED NAME EXTRACTION")
print("=" * 70)

# Test cases
test_cases = [
    ("who will win the Jean Silva vs Arnold Allen fight at UFC 324?", "Jean Silva", "Arnold Allen"),
    ("who will win Natalia Silva vs Rose Namajunas?", "Natalia Silva", "Rose Namajunas"),
    ("Kape vs Royval", "Kape", "Royval"),
    ("who will win the Brandon Royval vs Manel Kape fight?", "Brandon Royval", "Manel Kape"),
    ("Silva vs Allen", "Silva", "Allen"),
]

all_passed = True
for question, expected_a, expected_b in test_cases:
    fighter_a, fighter_b = extract_fighter_names(question)

    if fighter_a == expected_a and fighter_b == expected_b:
        print(f"✅ PASS: {question}")
        print(f"   Got: {fighter_a} vs {fighter_b}")
    else:
        print(f"❌ FAIL: {question}")
        print(f"   Expected: {expected_a} vs {expected_b}")
        print(f"   Got: {fighter_a} vs {fighter_b}")
        all_passed = False
    print()

print("=" * 70)
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)
