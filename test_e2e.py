import requests
import json
import time
import sys

BASE = "http://localhost:5000"

passed = 0
failed = 0

def test_step(uid, message, expected_node, step_label):
    global passed, failed
    r = requests.post(f"{BASE}/chat", json={"user_id": uid, "message": message})
    data = r.json()
    node = data["node_id"]
    if node == expected_node:
        passed += 1
        print(f"  OK   {step_label} -> {node}")
    else:
        failed += 1
        print(f"  FAIL {step_label}  expected={expected_node}  got={node}")
    return data

def test_llm_present(uid, message, label):
    global passed, failed
    r = requests.post(f"{BASE}/chat", json={"user_id": uid, "message": message})
    data = r.json()
    if data.get("llm") is True and len(data.get("text", "")) > 10:
        passed += 1
        print(f"  OK   {label}: LLM response present (len={len(data['text'])})")
    else:
        failed += 1
        print(f"  FAIL {label}: LLM response missing or too short")

def test_llm_boundary(uid, message, expected_node, label):
    global passed, failed
    r = requests.post(f"{BASE}/chat", json={"user_id": uid, "message": message})
    data = r.json()
    node = data["node_id"]
    text = data.get("text", "").lower()
    checks = []
    if node == expected_node:
        checks.append(f"node={node}")
    else:
        checks.append(f"EXPECTED_NODE={expected_node} GOT={node}")
    if "coach" in text or "counsel" in text:
        checks.append("redirect")
    if checks and node == expected_node:
        passed += 1
        print(f"  OK   {label}: {', '.join(checks)}")
    else:
        failed += 1
        print(f"  FAIL {label}: {', '.join(checks)}")

def test_life_map(uid, field, expected, label):
    global passed, failed
    r = requests.get(f"{BASE}/life-map/{uid}")
    lm = r.json()
    keys = field.split(".")
    val = lm
    for k in keys:
        val = val.get(k, {})
    if val == expected:
        passed += 1
        print(f"  OK   {label}: {field}={repr(val)}")
    else:
        failed += 1
        print(f"  FAIL {label}: {field} expected={repr(expected)} got={repr(val)}")


# -- JOURNEY 1 v2 E2E ---------------------------------------------------

print("\n" + "=" * 60)
print("JOURNEY 1 v2 - Emergency Independence (Jordan persona)")
print("=" * 60)

uid_j1 = "j1_e2e"
requests.post(f"{BASE}/reset/{uid_j1}", json={"tree": "j1"})
time.sleep(0.05)

test_step(uid_j1, "I got kicked out", "q1_danger",       "Step 1: Trigger -> danger check")
test_step(uid_j1, "no",                 "q2_trusted",     "Step 2: Not in danger -> trusted person")
test_step(uid_j1, "no",                 "q3_shelter",     "Step 3: Alone -> shelter tonight")
test_step(uid_j1, "no",                 "q4_minor",       "Step 4: No shelter -> shelter msg -> minor check")
test_step(uid_j1, "18 or older",        "q5_id",          "Step 5: Adult -> ID check")
test_step(uid_j1, "yes",                "q6_phone",       "Step 6: Has ID -> phone check")
test_step(uid_j1, "yes",                "q7_money",       "Step 7: Has phone -> money")
test_step(uid_j1, "$0",                 "q8_transport",   "Step 8: $0 cash -> transport")
test_step(uid_j1, "none",               "q9_job",         "Step 9: No transport -> job")
test_step(uid_j1, "no",                 "q10_bank",       "Step 10: No job -> bank")
test_step(uid_j1, "no",                 "q11_city",       "Step 11: No bank -> city")
test_step(uid_j1, "Chicago",            "q12_education",  "Step 12: Free-text city -> education")
test_step(uid_j1, "some college",       "plan_72hr",      "Step 13: Education -> 72hr plan")
test_step(uid_j1, "continue",           "plan_employment","Step 14: -> employment plan")
test_step(uid_j1, "continue",           "plan_housing",   "Step 15: -> housing plan")
test_step(uid_j1, "continue",           "gate_upgrade",   "Step 16: -> upgrade gate")
test_step(uid_j1, "free",               "plan_ongoing",   "Step 17: Free path -> ongoing")

test_life_map(uid_j1, "crisis.in_danger",    "No",              "J1 crisis.in_danger")
test_life_map(uid_j1, "crisis.is_minor",     "No, 18 or older", "J1 crisis.is_minor")
test_life_map(uid_j1, "profile.city",        "Chicago",         "J1 profile.city")
test_life_map(uid_j1, "crisis.status",       "stabilized",      "J1 crisis.status")


# -- JOURNEY 2 v2 E2E ---------------------------------------------------

print("\n" + "=" * 60)
print("JOURNEY 2 v2 - Aged Out of Foster Care (Maria persona)")
print("=" * 60)

uid_j2 = "j2_e2e"
requests.post(f"{BASE}/reset/{uid_j2}", json={"tree": "j2"})
time.sleep(0.05)

test_step(uid_j2, "aged out of foster care","q1_danger",        "Step 1: Trigger -> danger check")
test_step(uid_j2, "no",                      "q2_shelter",       "Step 2: Not in danger -> shelter")
test_step(uid_j2, "no",                      "q3_caseworker",    "Step 3: No shelter -> caseworker")
test_step(uid_j2, "no",                      "q4_extended_care", "Step 4: No caseworker -> extended care")
test_step(uid_j2, "yes",                     "msg_extended_care","Step 5: Under 21 -> ext care msg (waits)")
test_step(uid_j2, "ready",                   "q5_id",            "Step 6: Reply ready -> ID check")
test_step(uid_j2, "yes",                     "q6_phone",         "Step 7: Has ID -> phone")
test_step(uid_j2, "yes",                     "q7_money",         "Step 8: Has phone -> money")
test_step(uid_j2, "$1 - $100",               "q8_transport",     "Step 9: $1-100 -> transport")
test_step(uid_j2, "bus pass",                "q9_job",           "Step 10: Bus -> job")
test_step(uid_j2, "no",                      "q10_bank",         "Step 11: No job -> bank")
test_step(uid_j2, "no",                      "q11_city",         "Step 12: No bank -> city")
test_step(uid_j2, "Los Angeles",             "q12_education",    "Step 13: Free-text city -> education")
test_step(uid_j2, "want college",            "plan_benefits",    "Step 14: College path -> benefits plan")
test_step(uid_j2, "continue",                "plan_housing",     "Step 15: -> housing plan")
test_step(uid_j2, "continue",                "plan_employment",  "Step 16: -> employment plan")
test_step(uid_j2, "continue",                "plan_education",   "Step 17: -> education plan")
test_step(uid_j2, "continue",                "gate_upgrade",     "Step 18: -> upgrade gate")
test_step(uid_j2, "free",                    "plan_ongoing",     "Step 19: Free path -> ongoing")

test_life_map(uid_j2, "crisis.in_danger",    "No",              "J2 crisis.in_danger")
test_life_map(uid_j2, "foster.has_caseworker", False,           "J2 foster.has_caseworker")
test_life_map(uid_j2, "foster.extended_care_eligible", True,    "J2 foster.extended_care_eligible")
test_life_map(uid_j2, "profile.city",        "Los Angeles",     "J2 profile.city")

r = requests.get(f"{BASE}/life-map/{uid_j2}")
ep = r.json().get("education", {}).get("education_path", "")
if "want college" in ep:
    passed += 1
    print(f"  OK   J2 education_path contains 'want college': {repr(ep)}")
else:
    failed += 1
    print(f"  FAIL J2 education_path: got={repr(ep)}")


# -- LLM INTEGRATION TESTS -----------------------------------------------

print("\n" + "=" * 60)
print("LLM INTEGRATION TESTS")
print("=" * 60)

test_llm_present("llm_test1", "I got kicked out", "LLM generates J1 response")
test_llm_present("llm_test2", "aged out of foster care", "LLM generates J2 response")

# Boundary: user asks for therapy — should redirect, stay on current node
uid_bound = "boundary_test"
requests.post(f"{BASE}/reset/{uid_bound}", json={"tree": "j1"})
requests.post(f"{BASE}/chat", json={"user_id": uid_bound, "message": "I got kicked out"})
requests.post(f"{BASE}/chat", json={"user_id": uid_bound, "message": "no"})
requests.post(f"{BASE}/chat", json={"user_id": uid_bound, "message": "no"})
requests.post(f"{BASE}/chat", json={"user_id": uid_bound, "message": "no"})
requests.post(f"{BASE}/chat", json={"user_id": uid_bound, "message": "18 or older"})
test_llm_boundary(uid_bound, "I need therapy I am really depressed", "q5_id",
                  "Boundary: therapy request redirects properly")


# -- MULTI-TREE ROUTING --------------------------------------------------

print("\n" + "=" * 60)
print("MULTI-TREE ROUTING")
print("=" * 60)

uid_r1 = "route_j1_test"
r = requests.post(f"{BASE}/reset/{uid_r1}", json={"tree": "j1"})
r = requests.post(f"{BASE}/chat", json={"user_id": uid_r1, "message": "I got kicked out of my house"})
tree = r.json().get("tree", "unknown")
if tree == "j1":
    passed += 1
    print(f"  OK   existing j1 session + 'kicked out' -> tree={tree}")
else:
    failed += 1
    print(f"  FAIL existing j1 session -> expected=j1 got={tree}")

uid_r2 = "route_j2_fresh"
r = requests.post(f"{BASE}/chat", json={"user_id": uid_r2, "message": "I aged out of foster care"})
tree = r.json().get("tree", "unknown")
if tree == "j2":
    passed += 1
    print(f"  OK   fresh session + 'aged out of foster care' -> tree={tree}")
else:
    failed += 1
    print(f"  FAIL fresh session -> expected=j2 got={tree}")

uid_r3 = "route_default_fresh"
r = requests.post(f"{BASE}/chat", json={"user_id": uid_r3, "message": "I need help with life"})
tree = r.json().get("tree", "unknown")
if tree == "j1":
    passed += 1
    print(f"  OK   unmatched phrase -> tree={tree} (default)")
else:
    failed += 1
    print(f"  FAIL unmatched phrase -> expected=j1 got={tree}")

uid_r4 = "route_j1_fresh"
r = requests.post(f"{BASE}/chat", json={"user_id": uid_r4, "message": "I just got kicked out"})
tree = r.json().get("tree", "unknown")
if tree == "j1":
    passed += 1
    print(f"  OK   fresh session + 'kicked out' -> tree={tree}")
else:
    failed += 1
    print(f"  FAIL fresh session -> expected=j1 got={tree}")


# -- SUMMARY ------------------------------------------------------------

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("All tests passed.")
