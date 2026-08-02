"""
Alex LLM Integration Module
Uses Gemini Interactions API to generate Alex's natural-language responses.
Flask stays the brain (routing, Life Map, safety) — Gemini is the voice.
"""

from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL = "gemini-3.1-flash-lite"
_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are Alex, an AI Life Navigator for young adults aged 16-25. You are a structured life coach specializing in independent living skills.

Your personality:
- Direct but warm. No sugarcoating, no shaming.
- Calm under crisis. You triage, you don't panic.
- Structured. Steps, checklists, timelines — not essays.
- Persistent. You remember everything and follow up.

Core principles:
1. Safety first. If in danger, stop coaching and give crisis resources. No paywall, no delay.
2. Autonomy, not dependency. Every answer teaches a skill.
3. No judgment. "Let's work with where you are."
4. Never lie or exaggerate. Give official .gov links if you don't know.
5. Freemium boundaries. Crisis help is always free. Mention premium only after stabilization.

Voice rules:
- Use "you" and "I". Never third person.
- Sentences short. Paragraphs 1-3 lines max.
- Bold only for deadlines, dollar amounts, danger warnings.
- Bulleted lists for action items.
- No emojis unless the user uses one first.
- Don't say "I understand" or "I hear you" more than once per conversation.

Boundaries:
- No therapy. "I'm a coach, not a counselor."
- No legal advice. "I can give you state resources, but a lawyer should advise you."
- No medical advice. "Please call 911 or go to an ER."
- No promises. "This improves your odds, but I can't promise results."
- No philosophizing. No quotes, no metaphors.
- If user is abusive/hostile, stay calm 3x then disengage gracefully.

Upgrade gate: Never say "that's premium-only." Always offer the free alternative first.
Crisis hotlines (always free): 988, 1-800-799-7233, 1-800-RUNAWAY, 211"""


def _build_prompt(node, life_map, history):
    node_type = node.get("type", "question")
    node_text = node.get("text", "")
    tier = node.get("tier", "")
    options = node.get("options", [])
    why = node.get("why_alex_asks", "")

    parts = []

    if history:
        recent = history[-6:]
        history_text = "\n".join(
            f"User: {h.get('user', '')}\nAlex: {h.get('alex', '')}" for h in recent
        )
        parts.append(f"Recent conversation:\n{history_text}")

    parts.append(f"Current phase: {tier}")
    parts.append(f"What Alex needs to say now: {node_text}")

    if why:
        parts.append(f"Why this matters: {why}")

    if options:
        opt_labels = [o["label"] for o in options]
        parts.append(f"Response options to present: {opt_labels}")

    summary = summarize_life_map(life_map)
    if summary:
        parts.append(f"User's current situation (Life Map): {summary}")

    context = "\n\n".join(parts)

    return context


def summarize_life_map(life_map):
    if not life_map:
        return ""
    c = life_map.get("crisis", {})
    p = life_map.get("profile", {})
    e = life_map.get("employment", {})
    ed = life_map.get("education", {})
    f = life_map.get("foster", {})

    parts = []
    if c.get("in_danger"):
        parts.append(f"In danger: {c['in_danger']}")
    if c.get("immediate_shelter"):
        parts.append(f"Has shelter tonight: {c['immediate_shelter']}")
    if c.get("is_minor") is not None:
        parts.append(f"Is minor: {c['is_minor']}")
    if c.get("has_idsafe") is not None:
        parts.append(f"Has ID: {c['has_idsafe']}")
    if c.get("has_phone") is not None:
        parts.append(f"Phone working: {c['has_phone']}")
    if c.get("liquid_cash") is not None:
        parts.append(f"Cash: {c['liquid_cash']}")
    if c.get("transportation"):
        parts.append(f"Transport: {c['transportation']}")
    if c.get("has_bank_account") is not None:
        parts.append(f"Bank account: {c['has_bank_account']}")
    if p.get("city"):
        parts.append(f"City: {p['city']}")
    if ed.get("level"):
        parts.append(f"Education: {ed['level']}")
    if e.get("has_job") is not None:
        parts.append(f"Has job: {e['has_job']}")
    if f.get("has_caseworker") is not None:
        parts.append(f"Has caseworker: {f['has_caseworker']}")
    if f.get("extended_care_eligible") is not None:
        parts.append(f"Extended care eligible: {f['extended_care_eligible']}")

    return "; ".join(parts) if parts else ""


def generate_alex_response(node, life_map, history=None):
    """
    Generate Alex's natural-language response for the current node.
    
    Args:
        node: dict with type, text, options, why_alex_asks, tier
        life_map: dict of user's current Life Map data
        history: list of {user, alex} dicts (recent conversation)
    
    Returns:
        str: Alex's response text
    """
    client = _get_client()
    context = _build_prompt(node, life_map, history or [])

    full_prompt = f"""{SYSTEM_PROMPT}

---
{context}
---

Generate what Alex says now. Your response must be Alex speaking directly to the user (no narration, no stage directions). Use contractions (I'm, you're, let's, don't). If the node lists response options, include them naturally at the end. Keep it concise — 2-4 sentences unless it's a detailed plan or resource list.

If the user goes off-topic or asks for something Alex can't do (therapy, legal advice, medical advice, weather, chitchat), gently redirect back to the current question. Always mention the free alternative before suggesting premium."""

    try:
        interaction = client.interactions.create(
            model=MODEL,
            input=full_prompt,
        )
        return interaction.output_text.strip()
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return node.get("text", "")


def match_intent(user_message, options):
    """Use LLM to match a free-form user reply to the best option. Returns label or None."""
    client = _get_client()
    option_labels = [o if isinstance(o, str) else o.get("label", str(o)) for o in options]
    options_text = "\n".join(f"- {opt}" for opt in option_labels)

    prompt = f"""A young adult is talking to Alex, an AI life coach. Alex asked a question and gave these options:

{options_text}

The user replied: "{user_message}"

Your job: figure out which option the user meant, even if they said it differently. Look for the MEANING, not just keywords.
Examples:
- "nah i'm good" = No
- "yep got one" = Yes
- "I have mobile data" = Yes (implies phone works)
- "don't have anything" = No
- "about 5 bucks" or "around 20" = $1-100 (any amount $1-$99)
- "nothing, zero, broke, dead broke" = $0
- "i got about a hundred" or "maybe 200" = $100+
- "I drive an old Honda" = Car
- "I walk everywhere" = None
- "some high school, didn't finish, never went" = Some high school
- "got my GED" = High school diploma/GED
- "no ID, lost it, nothing on me" = No, nothing
- "got my birth certificate" = Yes, at least one (any form of ID)

Reply with ONLY the exact option text. If truly no match, reply ONLY "NO_MATCH"."""

    try:
        interaction = client.interactions.create(model=MODEL, input=prompt)
        result = interaction.output_text.strip()
        if result.upper() == "NO_MATCH":
            return None
        for opt in option_labels:
            if opt.lower() in result.lower() or result.lower() in opt.lower():
                return opt
        return None
    except Exception as e:
        print(f"[LLM INTENT ERROR] {e}")
        return None


def generate_plan_response(node, life_map, history=None):
    """
    Generate Alex's response for action_plan nodes.
    Includes the structured checklist tasks with conditions filtered.
    """
    client = _get_client()
    tasks = node.get("tasks", [])

    active_tasks = []
    for t in tasks:
        active_tasks.append(f"- Day {t.get('day')}: {t['task']}")

    task_list = "\n".join(active_tasks)
    context = _build_prompt(node, life_map, history or [])
    summary = summarize_life_map(life_map)

    full_prompt = f"""{SYSTEM_PROMPT}

---
Current phase: {node.get('tier', 'plan')}
User's situation: {summary}

Alex needs to present this action plan:
{node.get('text', '')}

Tasks:
{task_list}
---

Generate Alex's message introducing this plan to the user. Be warm and encouraging. Briefly explain why each section matters. Keep it practical and action-oriented. End with a clear next step (like "Reply 'continue' when you're ready" or similar)."""

    try:
        interaction = client.interactions.create(
            model=MODEL,
            input=full_prompt,
        )
        return interaction.output_text.strip()
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return node.get("text", "")
