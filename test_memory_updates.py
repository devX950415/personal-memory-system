"""
Test script to demonstrate memory update functionality
"""

import requests
import json
import time

API_URL = "http://localhost:8888"
TEST_USER_ID = "test_user_updates"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def send_message(message):
    print(f"\n📨 Sending: '{message}'")
    response = requests.post(
        f"{API_URL}/messages",
        json={"user_id": TEST_USER_ID, "message": message}
    )
    result = response.json()
    
    if result.get("extracted_memories"):
        print("✓ Extracted:")
        for mem in result["extracted_memories"]:
            print(f"  - {mem['field']}: {mem['value']} ({mem['event']})")
    else:
        print("  (No memories extracted)")
    
    return result

def get_memories():
    response = requests.get(f"{API_URL}/users/{TEST_USER_ID}/memories/raw")
    memories = response.json()["memories"]
    print("\n💾 Current Memories:")
    print(json.dumps(memories, indent=2))
    return memories

def delete_memories():
    requests.delete(f"{API_URL}/users/{TEST_USER_ID}/memories")
    print("🗑️  Deleted all memories")

# Test scenarios
print_section("TEST 1: Initial Data")
delete_memories()
send_message("My name is John, I'm 28 years old, and I work at Google")
send_message("I like pizza, hiking, and coding")
send_message("My skills are Python, Java, and React")
get_memories()

print_section("TEST 2: Update Age (Replacement)")
send_message("I'm now 29 years old")
memories = get_memories()
assert memories.get("age") == 29, "Age should be updated to 29"
print("✓ Age correctly updated")

print_section("TEST 3: Update Company (Replacement)")
send_message("I now work at Microsoft")
memories = get_memories()
assert memories.get("company") == "Microsoft", "Company should be updated to Microsoft"
print("✓ Company correctly updated")

print_section("TEST 4: Add to List")
send_message("I also like swimming")
memories = get_memories()
assert "swimming" in [like.lower() for like in memories.get("likes", [])], "Swimming should be added"
print("✓ Swimming added to likes")

print_section("TEST 5: Remove from List")
send_message("I don't like pizza anymore")
memories = get_memories()
assert "pizza" not in [like.lower() for like in memories.get("likes", [])], "Pizza should be removed"
print("✓ Pizza removed from likes")

print_section("TEST 6: Replace Entire List")
send_message("My skills are now TypeScript, Go, and Rust")
memories = get_memories()
skills = [s.lower() for s in memories.get("skills", [])]
assert "typescript" in skills and "go" in skills and "rust" in skills, "New skills should be present"
assert "python" not in skills and "java" not in skills and "react" not in skills, "Old skills should be removed"
print("✓ Skills list completely replaced")

print_section("TEST 7: Conflict Resolution")
send_message("I like tomatoes")
send_message("Actually, I dislike tomatoes")
memories = get_memories()
likes = [like.lower() for like in memories.get("likes", [])]
dislikes = [dislike.lower() for dislike in memories.get("dislikes", [])]
assert "tomatoes" not in likes, "Tomatoes should not be in likes"
assert "tomatoes" in dislikes, "Tomatoes should be in dislikes"
print("✓ Conflict resolution working")

print_section("ALL TESTS PASSED! ✓")
delete_memories()
