"""
Test Alex's voice across 6 scenarios before wiring into Flask.
Run: python test_voice.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from llm import generate_alex_response, generate_plan_response

BASE = os.path.dirname(__file__)

# Load J1 and J2 trees
j1_tree = json.load(open(os.path.join(BASE, "..", "Session-2", "Source", "01-Decision-Tree-v2.json")))
j2_tree = json.load(open(os.path.join(BASE, "..", "Session-5", "Source", "01-Decision-Tree-v2.json")))

def get_node(tree, node_id):
    for n in tree["nodes"]:
        if n["id"] == node_id:
            return n
    return None


def test(title, tree_key, node_id, life_map, history=None):
    tree = j1_tree if tree_key == "j1" else j2_tree
    node = get_node(tree, node_id)
    print(f"\n{'='*60}")
    print(f"SCENARIO: {title}")
    print(f"  Node: {node_id} ({node.get('tier', '')})")
    print(f"  Hardcoded text: {node.get('text', '')[:100]}...")
    print(f"{'='*60}")

    if node.get("type") == "action_plan":
        response = generate_plan_response(node, life_map, history)
    else:
        response = generate_alex_response(node, life_map, history)

    print(f"\nALEX'S RESPONSE:\n{response}\n")


# ─── SCENARIO 1: Crisis — Danger check (J1) ───
test(
    "1. Crisis: User says they got kicked out, danger check",
    "j1",
    "q1_danger",
    {"crisis": {"in_danger": None}},
    [{"user": "I just got kicked out of my house", "alex": ""}],
)

# ─── SCENARIO 2: Normal flow — Shelter tonight (J1) ───
test(
    "2. Normal flow: Asking if user has shelter",
    "j1",
    "q3_shelter",
    {"crisis": {"in_danger": "No", "with_trusted_person": "No"}},
    [
        {"user": "I got kicked out", "alex": "I'm sorry that happened..."},
        {"user": "no", "alex": "Are you with someone you trust?"},
        {"user": "no", "alex": ""},
    ],
)

# ─── SCENARIO 3: Foster-specific — Caseworker check (J2) ───
test(
    "3. Foster-specific: Do you still have a caseworker?",
    "j2",
    "q3_caseworker",
    {
        "crisis": {"in_danger": "No", "immediate_shelter": "No"},
        "foster": {},
    },
    [
        {"user": "I aged out of foster care", "alex": "Aging out is a huge transition..."},
        {"user": "no", "alex": "Do you have a safe place to sleep tonight?"},
        {"user": "no", "alex": "Let's find one now..."},
    ],
)

# ─── SCENARIO 4: Boundary — User asks for therapy ───
test(
    "4. Boundary: User asks Alex for therapy/counseling",
    "j1",
    "q10_bank",
    {
        "crisis": {"in_danger": "No", "immediate_shelter": "Yes", "has_idsafe": True, "has_phone": True, "liquid_cash": "$100+", "transportation": "Bus pass"},
        "employment": {"has_job": True},
        "profile": {"city": "Manila"},
    },
    [
        {"user": "I got kicked out", "alex": "..."},
        {"user": "no", "alex": "..."},
        {"user": "yes", "alex": "..."},
        {"user": "no, 18 or older", "alex": "..."},
        {"user": "yes", "alex": "..."},
        {"user": "yes", "alex": "..."},
        {"user": "$100+", "alex": "..."},
        {"user": "bus pass", "alex": "..."},
        {"user": "yes", "alex": "..."},
        {"user": "I think I need therapy. I'm really depressed.", "alex": ""},
    ],
)

# ─── SCENARIO 5: Upgrade gate — "Can you help me talk to my parents?" ───
test(
    "5. Upgrade gate: User asks for family mediation",
    "j1",
    "gate_upgrade",
    {
        "crisis": {"status": "stabilized", "in_danger": "No", "immediate_shelter": "Yes"},
        "profile": {"city": "Cebu"},
        "employment": {"has_job": False},
        "education": {"level": "High school diploma/GED"},
    },
    [
        {"user": "Can you help me talk to my parents?", "alex": ""},
    ],
)

# ─── SCENARIO 6: Off-topic — User asks about weather ───
test(
    "6. Off-topic: User asks about something unrelated",
    "j1",
    "q6_phone",
    {
        "crisis": {"in_danger": "No", "immediate_shelter": "No", "has_idsafe": True},
    },
    [
        {"user": "What's the weather like today?", "alex": ""},
    ],
)

print("\n" + "=" * 60)
print("VOICE TESTING COMPLETE — Review responses above")
print("=" * 60)
