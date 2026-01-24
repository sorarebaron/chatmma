#!/usr/bin/env python3
"""Test the O'Malley apostrophe fix."""
import re

def extract_fighter_names_new(question):
    """Extract fighter names with apostrophe support."""
    question_lower = question.lower()

    vs_patterns = [" vs ", " vs. ", " versus ", " v ", " against "]
    for pattern in vs_patterns:
        if pattern in question_lower:
            parts = question_lower.split(pattern)
            if len(parts) == 2:
                # Extract up to 2 words before "vs"
                left_words = parts[0].strip().split()
                fighter_a_words = left_words[-2:] if len(left_words) >= 2 else left_words[-1:]
                fighter_a = ' '.join(fighter_a_words)
                # Remove punctuation but keep apostrophes
                fighter_a = re.sub(r'[^\w\s\']', '', fighter_a)

                # Extract up to 2 words after "vs"
                right_words = parts[1].strip().split()
                fighter_b_words = right_words[:2] if len(right_words) >= 2 else right_words[:1]
                fighter_b = ' '.join(fighter_b_words)
                # Remove punctuation but keep apostrophes
                fighter_b = re.sub(r'[^\w\s\']', '', fighter_b)

                return fighter_a.title(), fighter_b.title()
    return None, None

print("=" * 70)
print("TESTING O'MALLEY APOSTROPHE FIX")
print("=" * 70)

# Test cases
test_cases = [
    ("who will win the sean o'malley vs yadong song fight at ufc 324?", "Sean O'Malley", "Yadong Song"),
    ("who will win the Sean O'Malley vs Yadong Song fight?", "Sean O'Malley", "Yadong Song"),
    ("Sean O'Malley vs Song", "Sean O'Malley", "Song"),
    ("who will win Natalia Silva vs Rose Namajunas?", "Natalia Silva", "Rose Namajunas"),
    ("Jean Silva vs Arnold Allen", "Jean Silva", "Arnold Allen"),
]

all_passed = True
for question, expected_a, expected_b in test_cases:
    fighter_a, fighter_b = extract_fighter_names_new(question)

    if fighter_a == expected_a and fighter_b == expected_b:
        print(f"✅ PASS: {question}")
        print(f"   Extracted: '{fighter_a}' vs '{fighter_b}'")
    else:
        print(f"❌ FAIL: {question}")
        print(f"   Expected: '{expected_a}' vs '{expected_b}'")
        print(f"   Got: '{fighter_a}' vs '{fighter_b}'")
        all_passed = False
    print()

print("=" * 70)
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)
