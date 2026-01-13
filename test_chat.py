#!/usr/bin/env python
"""Test chat interface with a sample query"""
import sys
sys.path.append('scripts')
from chat_interface import chat

# Test query
query = "Who do analysts pick for the UFC 323 main event between Petr Yan and Merab Dvalishvili?"

print(f"\nQUERY: {query}\n")
print("RESPONSE:")
print("="*60)
response = chat(query)
print(response)
print("="*60)
