#!/usr/bin/env python3
"""
Diagnose CSV file for problematic rows.
"""
import csv
import sys

def diagnose_csv(csv_file):
    """Check CSV for rows that will cause issues."""

    print(f"Diagnosing: {csv_file}")
    print("=" * 70)

    problems = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # start=2 (row 1 is header)
            # Check for empty fight
            fight = row.get('fight', '').strip()

            if not fight:
                problems.append(f"Row {row_num}: Empty fight column")
                continue

            # Check for missing " vs "
            if ' vs ' not in fight and ' vs. ' not in fight:
                problems.append(f"Row {row_num}: Fight '{fight}' missing ' vs ' separator")
                continue

            # Check if it splits into exactly 2 fighters
            if ' vs ' in fight:
                fighters = fight.split(' vs ')
            elif ' vs. ' in fight:
                fighters = fight.split(' vs. ')
            else:
                fighters = []

            if len(fighters) != 2:
                problems.append(f"Row {row_num}: Fight '{fight}' splits into {len(fighters)} parts (need 2)")
                continue

            # Check if both fighter names are non-empty
            if not fighters[0].strip() or not fighters[1].strip():
                problems.append(f"Row {row_num}: Fight '{fight}' has empty fighter name")

    print(f"Checked {row_num - 1} rows\n")

    if problems:
        print(f"❌ Found {len(problems)} problems:\n")
        for problem in problems:
            print(f"  {problem}")
    else:
        print("✅ No problems found!")

    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_csv.py <csv_file>")
        sys.exit(1)

    diagnose_csv(sys.argv[1])
