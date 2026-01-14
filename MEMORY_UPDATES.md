# Memory Update Behavior

This document explains how PersonalMem handles different types of memory updates.

## Update Types

PersonalMem supports three types of memory operations:

### 1. ADD (Append to existing data)
### 2. REPLACE (Overwrite existing data)
### 3. REMOVE (Delete data)

---

## How It Works

### Single-Value Fields (Strings, Numbers)

**Always replaced automatically:**

```
Current: {"age": 28}
Message: "I'm now 29"
Result:  {"age": 29}
```

```
Current: {"company": "Google"}
Message: "I work at Microsoft"
Result:  {"company": "Microsoft"}
```

### Array Fields (Lists)

**Default behavior: ADD (append unique items)**

```
Current: {"skills": ["Python", "Java"]}
Message: "I also know React"
Result:  {"skills": ["Python", "Java", "React"]}
```

**Explicit replacement: Use "replace_" prefix**

```
Current: {"skills": ["Python", "Java", "React"]}
Message: "My skills are now TypeScript and Go"
LLM:     {"replace_skills": ["TypeScript", "Go"]}
Result:  {"skills": ["TypeScript", "Go"]}
```

**Removal: Use "remove_" prefix**

```
Current: {"skills": ["Python", "Java", "React"]}
Message: "I forgot Java"
LLM:     {"remove_skills": ["Java"]}
Result:  {"skills": ["Python", "React"]}
```

---

## LLM Detection Rules

The LLM automatically detects the user's intent:

### Replacement Indicators

| User Message | Detected As | Result |
|--------------|-------------|--------|
| "I'm now 29" | REPLACE age | `{"age": 29}` |
| "I work at Microsoft" | REPLACE company | `{"company": "Microsoft"}` |
| "My skills are Python and Java" | REPLACE skills | `{"replace_skills": ["Python", "Java"]}` |
| "I only speak English now" | REPLACE languages | `{"replace_languages": ["English"]}` |

### Addition Indicators

| User Message | Detected As | Result |
|--------------|-------------|--------|
| "I also like pizza" | ADD to likes | `{"likes": ["pizza"]}` |
| "I also know React" | ADD to skills | `{"skills": ["React"]}` |
| "I speak Spanish too" | ADD to languages | `{"languages": ["Spanish"]}` |

### Removal Indicators

| User Message | Detected As | Result |
|--------------|-------------|--------|
| "I don't like pizza anymore" | REMOVE from likes | `{"remove_likes": ["pizza"]}` |
| "I forgot Java" | REMOVE from skills | `{"remove_skills": ["Java"]}` |
| "I no longer work at Google" | REMOVE company | `{"remove_company": true}` |

---

## Context-Aware Updates

The LLM considers existing data when deciding between ADD and REPLACE:

### Example 1: Age Update

```
Current: {"age": 28}
Message: "I'm 29"
→ Detected as REPLACE (not ADD)
Result: {"age": 29}
```

### Example 2: Skills Update

```
Current: {"skills": ["Python"]}
Message: "I also know Java"
→ Detected as ADD (keyword "also")
Result: {"skills": ["Python", "Java"]}

Message: "My skills are Java and React"
→ Detected as REPLACE (complete list provided)
Result: {"skills": ["Java", "React"]}
```

---

## Conflict Resolution

Certain fields are mutually exclusive:

### Likes vs Dislikes

```
Current: {"likes": ["pizza"], "dislikes": ["tomatoes"]}
Message: "I like tomatoes"
Result:  {"likes": ["pizza", "tomatoes"], "dislikes": []}
```

```
Current: {"likes": ["pizza", "tomatoes"]}
Message: "I dislike tomatoes"
Result:  {"likes": ["pizza"], "dislikes": ["tomatoes"]}
```

---

## Examples

### Scenario 1: Updating Job Information

```bash
# Initial
Message: "I work at Google as a Senior Developer"
Result:  {"company": "Google", "role": "Senior Developer"}

# Update company
Message: "I now work at Microsoft"
Result:  {"company": "Microsoft", "role": "Senior Developer"}

# Update role
Message: "I'm now a Tech Lead"
Result:  {"company": "Microsoft", "role": "Tech Lead"}
```

### Scenario 2: Managing Skills

```bash
# Initial
Message: "I know Python, Java, and React"
Result:  {"skills": ["Python", "Java", "React"]}

# Add skill
Message: "I also learned TypeScript"
Result:  {"skills": ["Python", "Java", "React", "TypeScript"]}

# Remove skill
Message: "I forgot Java"
Result:  {"skills": ["Python", "React", "TypeScript"]}

# Replace all skills
Message: "My current skills are Go, Rust, and Kubernetes"
Result:  {"skills": ["Go", "Rust", "Kubernetes"]}
```

### Scenario 3: Preferences

```bash
# Initial
Message: "I like pizza, hiking, and coding"
Result:  {"likes": ["pizza", "hiking", "coding"]}

# Add preference
Message: "I also like swimming"
Result:  {"likes": ["pizza", "hiking", "coding", "swimming"]}

# Remove preference
Message: "I don't like pizza anymore"
Result:  {"likes": ["hiking", "coding", "swimming"]}

# Add dislike (conflict resolution)
Message: "I dislike hiking"
Result:  {"likes": ["coding", "swimming"], "dislikes": ["hiking"]}
```

---

## Testing Updates

Use the provided test script:

```bash
# Start the API
uvicorn api:app --reload --host 0.0.0.0 --port 8888

# Run tests
python test_memory_updates.py
```

The test script validates:
- Age updates (replacement)
- Company updates (replacement)
- Adding to lists
- Removing from lists
- Replacing entire lists
- Conflict resolution

---

## Troubleshooting

### Issue: Old data not being removed

**Cause:** LLM didn't detect replacement intent

**Solution:** Use explicit language:
- ❌ "I know Python and Java" (ambiguous)
- ✓ "My skills are now Python and Java" (clear replacement)
- ✓ "I only know Python and Java" (clear replacement)

### Issue: New data not being added

**Cause:** LLM detected replacement instead of addition

**Solution:** Use addition keywords:
- ✓ "I also like pizza"
- ✓ "I additionally know React"
- ✓ "I speak Spanish too"

### Issue: Data not being removed

**Cause:** Unclear removal intent

**Solution:** Use explicit removal language:
- ✓ "I don't like pizza anymore"
- ✓ "I forgot Java"
- ✓ "I no longer work at Google"

---

## API Response

The API returns detailed change information:

```json
{
  "success": true,
  "extracted_memories": [
    {
      "field": "age",
      "value": 29,
      "event": "UPDATE"
    },
    {
      "field": "skills",
      "value": ["Python", "Java"],
      "event": "REPLACE"
    },
    {
      "field": "likes",
      "value": ["pizza"],
      "event": "REMOVE"
    }
  ],
  "response_time_ms": 850
}
```

**Event Types:**
- `ADD` - New field created
- `UPDATE` - Existing field modified (append or replace)
- `REPLACE` - Entire field replaced
- `REMOVE` - Items removed from field
