#!/usr/bin/env python
"""Test chat interface with DFS query"""
import sys
sys.path.append('scripts')
from chat_interface import chat

# Test DFS query
query = "What are the best DFS picks for UFC 323?"

print(f"\nQUERY: {query}\n")
print("RESPONSE:")
print("="*60)
response = chat(query)
print(response)
print("="*60)
