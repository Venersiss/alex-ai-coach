from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone
from llm import generate_alex_response, generate_plan_response, match_intent

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

BASE = os.path.dirname(__file__)

TREE_PATHS = [
    ("j1", os.path.join(BASE, "data", "j1-decision-tree.json")),
    ("j2", os.path.join(BASE, "data", "j2-decision-tree.json")),
]

trees = {}
all_nodes = {}
for tree_key, path in TREE_PATHS:
    with open(path) as f:
        tree = json.load(f)
    trees[tree_key] = tree
    all_nodes[tree_key] = {n["id"]: n for n in tree["nodes"]}

sessions = {}

LIFE_MAP_TEMPLATE = json.load(
    open(os.path.join(BASE, "Life-Map-Schema.json"))
)

FOSTER_DEFAULTS = {
    "has_caseworker": None,
    "caseworker_name": None,
    "caseworker_phone": None,
    "ilp_coordinator_contact": None,
    "extended_care_eligible": None,
    "extended_care_enrolled": None,
    "aging_out_date": None,
    "transitional_program_enrolled": None,
    "transitional_program_name": None,
    "etv_applied": None,
    "etv_approved": None,
    "chafee_applied": None,
    "medicaid_until_26_verified": None,
    "state_tuition_waiver_eligible": None,
    "fup_voucher_applied": None,
}


def init_session(tree_key="j1"):
    tree = trees[tree_key]
    lm = {
        "version": 1,
        "profile": {"age": None, "state": None, "is_minor": False, "phone_working": None, "city": None},
        "crisis": {"status": "active", "trigger_event": tree_key,
                   "in_danger": None, "with_trusted_person": None, "immediate_shelter": None,
                   "is_minor": None, "has_idsafe": None, "has_phone": None, "liquid_cash": None,
                   "transportation": None, "has_bank_account": None, "hotline_contacted": None,
                   "first_alerted_at": datetime.now(timezone.utc).isoformat(), "stabilized_at": None},
        "employment": {"has_job": False, "current_job_title": None, "hourly_wage": None,
                       "hours_per_week": None, "job_history": [], "skills": [],
                       "income_lane_chosen": None, "foster_youth_program_enrolled": None},
        "education": {"level": None, "in_school": False, "school_name": None, "gpa": None,
                      "interested_in": [], "ged_in_progress": None, "currently_enrolled": None,
                      "education_path": None},
        "housing": {"current_situation": None, "path_chosen": None, "lease_ready_score": None,
                    "security_deposit_saved": None, "eviction_record": None},
        "plan": {"72hr_started_at": None, "72hr_completed_at": None, "72hr_tasks_completed": 0,
                 "employment_started_at": None, "employment_goal_set": None,
                 "housing_started_at": None, "next_check_in": None,
                 "benefits_started_at": None, "benefits_completed_at": None,
                 "benefits_tasks_completed": 0, "education_started_at": None,
                 "education_goal_set": None, "housing_path_chosen": None},
        "badges": [],
        "premium": {"is_subscribed": False, "subscription_tier": "free", "features_unlocked": [],
                    "upgrade_gate_shown_at": None, "upgrade_gate_accepted": None},
        "engagement": {"total_sessions": 0, "last_active_at": None, "consecutive_days_active": 0,
                       "messages_exchanged": 0, "average_session_length_minutes": 0,
                       "dropped_off_at_step": None, "nudge_count": 0},
        "consent": {"data_sharing_agreed": False, "mandatory_reporting_acknowledged": None,
                    "gdpr_opted_in": False, "opted_out_at": None},
    }
    if tree_key == "j2":
        lm["foster"] = dict(FOSTER_DEFAULTS)
        lm["profile"]["age_group"] = None
    return {"tree": tree_key, "current_node": "__welcome__", "life_map": lm, "history": []}


def get_node(tree_key, node_id):
    return all_nodes.get(tree_key, {}).get(node_id)


def match_tree(user_input):
    user_lower = user_input.lower()
    for tree_key in ["j2", "j1"]:
        tree = trees[tree_key]
        for phrase in tree.get("trigger_phrases", []):
            if phrase in user_lower:
                return tree_key
    return "j1"


def has_trigger(user_input):
    user_lower = user_input.lower()
    for tree in trees.values():
        for phrase in tree.get("trigger_phrases", []):
            if phrase in user_lower:
                return True
    return False


def _handle_welcome(session, user_input):
    """Show welcome or re-route to crisis flow if user mentions a trigger."""
    history = session.get("history", [])
    is_first = len(history) == 0
    user_lower = user_input.strip().lower()

    if user_lower and has_trigger(user_input):
        new_tree = match_tree(user_input)
        old_lm = session["life_map"]
        session.update(init_session(new_tree))
        session["life_map"] = old_lm
        session["tree"] = new_tree
        session["current_node"] = trees[new_tree]["root_node"]
        session["life_map"]["crisis"]["status"] = "active"
        return get_response(session, "")

    if not is_first and user_lower:
        if has_trigger(user_input):
            new_tree = match_tree(user_input)
            if new_tree != session.get("tree", "j1"):
                old_lm = session["life_map"]
                session.update(init_session(new_tree))
                session["life_map"] = old_lm
                session["tree"] = new_tree
                session["current_node"] = trees[new_tree]["root_node"]
                session["life_map"]["crisis"]["status"] = "active"
                return get_response(session, "")
            session["current_node"] = trees[new_tree]["root_node"]
            session["life_map"]["crisis"]["status"] = "active"
            return get_response(session, "")

    welcome_node = {
        "type": "question",
        "text": "Introduce yourself as Alex the AI Life Navigator. You help young adults (16-25) build independence. "
                "Tell them you can help with situations like getting kicked out, aging out of foster care, "
                "finding a job, going to college, or building life skills. "
                "Ask: 'What's going on? What do you need help with?' Keep it warm and welcoming, 3-4 sentences.",
        "tier": "context",
        "options": [
            {"label": "I got kicked out"},
            {"label": "I aged out of foster care"},
        ],
    }

    llm_text = None
    try:
        llm_text = generate_alex_response(welcome_node, session["life_map"], history)
    except Exception:
        pass

    text = llm_text or (
        "Hi, I'm Alex \u2014 your AI Life Navigator. I help young adults build independence, "
        "one step at a time. Whether you've been kicked out, aged out of foster care, "
        "or just need help with jobs, housing, or life skills \u2014 I've got your back. "
        "What's going on? What do you need help with?"
    )

    response = {
        "text": text,
        "options": ["I got kicked out", "I aged out of foster care"],
        "done": False,
        "llm": bool(llm_text),
        "welcome": True,
    }

    session["life_map"]["engagement"]["messages_exchanged"] += 1
    session["life_map"]["engagement"]["last_active_at"] = datetime.now(timezone.utc).isoformat()
    session["history"].append({"user": user_input, "alex": text})
    return response


def save_field(session, save_config, user_input, matched_label):
    if isinstance(save_config, list):
        for cfg in save_config:
            save_field(session, cfg, user_input, matched_label)
        return
    field = save_config.get("field", "")
    if "value" in save_config:
        value = save_config["value"]
    elif save_config.get("source") == "answer_is_yes":
        value = "yes" in (matched_label or user_input).lower()
    else:
        value = matched_label if matched_label else user_input
    if save_config.get("timestamp"):
        value = datetime.now(timezone.utc).isoformat()
    set_nested(session["life_map"], field, value)


def get_response(session, user_input):
    tree_key = session.get("tree", "j1")

    if session.get("current_node") == "__welcome__":
        return _handle_welcome(session, user_input)

    node = get_node(tree_key, session["current_node"])
    if not node:
        return {"text": "I'm not sure where we left off. Let's start over.", "done": True}

    fallback_text = node.get("text", "")
    response = {"text": fallback_text, "options": [], "done": False}
    node_type = node.get("type")
    user_lower = user_input.lower().strip()
    matched_label = None

    if node_type == "question":
        options = node.get("options", [])
        response["options"] = [opt["label"] for opt in options]
        if not options and user_lower:
            matched_label = user_input.strip()
            next_node = node.get("next_node", session["current_node"])
            session["current_node"] = next_node
            if "save_to_life_map" in node:
                save_field(session, node["save_to_life_map"], user_input, matched_label)
            session["history"].append({"user": user_input, "alex": ""})
            return get_response(session, "")
        if user_lower:
            for opt in options:
                opt_lower = opt["label"].lower()
                if opt_lower in user_lower or user_lower in opt_lower:
                    matched_label = opt["label"]
                    session["current_node"] = opt["next_node"]
                    if "save_to_life_map" in node:
                        save_field(session, node["save_to_life_map"], user_input, matched_label)
                    session["history"].append({"user": user_input, "alex": ""})
                    return get_response(session, "")
            matched_label = match_intent(user_input, options)
            if matched_label:
                for opt in options:
                    if opt["label"] == matched_label:
                        session["current_node"] = opt["next_node"]
                        if "save_to_life_map" in node:
                            save_field(session, node["save_to_life_map"], user_input, matched_label)
                        session["history"].append({"user": user_input, "alex": ""})
                        return get_response(session, "")

    elif node_type == "message":
        if node.get("resources"):
            response["resources"] = [{"label": r["label"], "url": r["url"]} for r in node["resources"]]
        wait = node.get("wait_for_reply")
        if wait and wait in user_lower:
            session["current_node"] = node.get("next_node", session["current_node"])
            matched_label = user_input
            if "save_to_life_map" in node:
                save_field(session, node["save_to_life_map"], user_input, matched_label)
            session["history"].append({"user": user_input, "alex": ""})
            return get_response(session, "")
        elif not wait:
            if "save_to_life_map" in node:
                save_field(session, node["save_to_life_map"], user_input, matched_label)
            session["current_node"] = node.get("next_node", session["current_node"])

    elif node_type == "form":
        response["fields"] = [{"key": f["key"], "label": f["label"], "type": f["type"]}
                              for f in node.get("fields", [])]
        if user_lower:
            session["current_node"] = node.get("next_node", session["current_node"])
            matched_label = user_input
            return get_response(session, "")

    elif node_type == "action_plan":
        tasks = node.get("tasks", [])
        response["checklist"] = [{"day": t.get("day"), "task": t["task"]} for t in tasks]
        if user_lower:
            session["current_node"] = node.get("next_node", session["current_node"])
            matched_label = user_input
            if "save_to_life_map" in node:
                save_field(session, node["save_to_life_map"], user_input, matched_label)
            return get_response(session, "")

    elif node_type == "upgrade_gate":
        response["premium_features"] = node.get("premium_features", [])
        if user_lower:
            if "premium" in user_lower or "upgrade" in user_lower:
                session["current_node"] = node.get("upgrade_node", node.get("free_continues"))
            else:
                session["current_node"] = node.get("free_continues", session["current_node"])
            matched_label = user_input
            return get_response(session, "")

    session["life_map"]["engagement"]["messages_exchanged"] += 1
    session["life_map"]["engagement"]["last_active_at"] = datetime.now(timezone.utc).isoformat()

    llm_text = None
    try:
        if node_type == "action_plan":
            llm_text = generate_plan_response(node, session["life_map"], session.get("history", []))
        else:
            llm_text = generate_alex_response(node, session["life_map"], session.get("history", []))
    except Exception:
        pass

    if llm_text:
        response["text"] = llm_text
        response["llm"] = True
    else:
        response["text"] = fallback_text
        response["llm"] = False

    session["history"].append({"user": user_input, "alex": response["text"]})
    return response


def set_nested(obj, path, value):
    keys = path.split(".")
    for key in keys[:-1]:
        obj = obj.setdefault(key, {})
    obj[keys[-1]] = value


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("user_id", "default")
    message = data.get("message", "")

    if user_id not in sessions:
        tree_key = match_tree(message) if message.strip() else "j1"
        sessions[user_id] = init_session(tree_key)

    session = sessions[user_id]
    response = get_response(session, message)
    response["node_id"] = session["current_node"]
    response["tree"] = session["tree"]
    return jsonify(response)


@app.route("/life-map/<user_id>", methods=["GET"])
def get_life_map(user_id):
    if user_id not in sessions:
        sessions[user_id] = init_session()
    return jsonify(sessions[user_id]["life_map"])


@app.route("/reset/<user_id>", methods=["POST"])
def reset(user_id):
    data = request.get_json(silent=True) or {}
    tree_key = data.get("tree", "j1")
    sessions[user_id] = init_session(tree_key)
    return jsonify({"status": "reset", "current_node": sessions[user_id]["current_node"], "tree": tree_key})


@app.route("/history/<user_id>", methods=["GET"])
def get_history(user_id):
    if user_id not in sessions:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "tree": sessions[user_id]["tree"],
        "node": sessions[user_id]["current_node"],
        "history": sessions[user_id].get("history", []),
    })

@app.route("/sessions", methods=["GET"])
def list_sessions():
    result = {}
    for uid, s in sessions.items():
        result[uid] = {
            "tree": s.get("tree"),
            "node": s.get("current_node"),
            "messages": len(s.get("history", [])),
        }
    return jsonify(result)

@app.route("/")
def index():
    from flask import send_file
    return send_file(os.path.join(BASE, "chat.html"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
