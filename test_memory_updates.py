"""
Integration tests for the v3 frontend-friendly API.

Run against a live instance:
    python test_memory_updates.py
"""

import requests

API_URL = "http://localhost:8888"
USER = "test_user_updates"


def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def chat(message):
    print(f"\n[chat] '{message}'")
    r = requests.post(f"{API_URL}/users/{USER}/messages", json={"message": message})
    r.raise_for_status()
    data = r.json()
    for m in data.get("extracted_memories", []):
        print(f"  - {m['field']}: {m['value']} ({m['event']})")
    return data


def patch(body):
    print(f"\n[patch] {body}")
    r = requests.patch(f"{API_URL}/users/{USER}", json=body)
    if r.status_code >= 400:
        print(f"  ERROR {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


def load():
    r = requests.get(f"{API_URL}/users/{USER}")
    r.raise_for_status()
    data = r.json()
    print(f"\n[memories] {data['memories']}")
    return data["memories"]


def wipe():
    requests.delete(f"{API_URL}/users/{USER}")
    print("[wipe]")


# --- LLM extraction path (unchanged behavior) ---
section("TEST 1: LLM extraction seeds the user")
wipe()
chat("My name is John, I'm 28, and I work at Google")
chat("I like pizza, hiking, and coding")
chat("My skills are Python, Java, and React")
mems = load()
assert mems.get("name") == "John"
assert mems.get("age") == 28

section("TEST 2: LLM update — age replacement")
chat("I'm now 29 years old")
mems = load()
assert mems.get("age") == 29
print("OK")

section("TEST 3: LLM update — company replacement")
chat("I now work at Microsoft")
mems = load()
assert mems.get("company") == "Microsoft"
print("OK")

# --- New direct PATCH actions ---
section("TEST 4: PATCH set scalar")
patch({"action": "set", "field": "favorite_color", "value": "blue"})
mems = load()
assert mems.get("favorite_color") == "blue"
print("OK")

section("TEST 5: PATCH append (single + list)")
patch({"action": "append", "field": "skills", "value": "Rust"})
patch({"action": "append", "field": "skills", "value": ["Go", "TypeScript"]})
mems = load()
sk = [s.lower() for s in mems.get("skills", [])]
for need in ("rust", "go", "typescript"):
    assert need in sk, f"missing {need} in skills={sk}"
print("OK")

section("TEST 6: PATCH remove (single item)")
patch({"action": "remove", "field": "skills", "value": "Java"})
mems = load()
sk = [s.lower() for s in mems.get("skills", [])]
assert "java" not in sk
print("OK")

section("TEST 7: PATCH delete (whole field)")
patch({"action": "delete", "field": "favorite_color"})
mems = load()
assert "favorite_color" not in mems
print("OK")

section("TEST 8: PATCH set on list overwrites whole list")
patch({"action": "set", "field": "skills", "value": ["Elixir"]})
mems = load()
assert mems.get("skills") == ["Elixir"]
print("OK")

section("TEST 9: PATCH bulk_set multi-field")
patch({"action": "bulk_set", "values": {"hometown": "Boston", "age": 30, "languages": ["English", "Spanish"]}})
mems = load()
assert mems.get("hometown") == "Boston"
assert mems.get("age") == 30
assert mems.get("languages") == ["English", "Spanish"]
print("OK")

section("TEST 10: LLM conflict resolution still works")
chat("I like tomatoes")
chat("Actually, I dislike tomatoes")
mems = load()
likes = [v.lower() for v in mems.get("likes", [])]
dislikes = [v.lower() for v in mems.get("dislikes", [])]
assert "tomatoes" not in likes
assert "tomatoes" in dislikes
print("OK")

section("TEST 11: Validation — bad PATCH body returns 400")
r = requests.patch(f"{API_URL}/users/{USER}", json={"action": "nonsense"})
assert r.status_code == 400, r.status_code
r = requests.patch(f"{API_URL}/users/{USER}", json={"action": "set", "field": "x"})  # missing value
assert r.status_code == 400, r.status_code
print("OK")

section("TEST 12: DELETE returns empty state, not 404")
r = requests.delete(f"{API_URL}/users/{USER}")
r.raise_for_status()
data = r.json()
assert data["has_memories"] is False
assert data["field_count"] == 0
print("OK")

section("ALL TESTS PASSED")
