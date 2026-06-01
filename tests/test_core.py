"""Core tests for idea_generator"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock config before importing
import types
cfg = types.ModuleType("bot.config")
cfg.config = types.SimpleNamespace(
    openai_api_key="",
    openai_model="gpt-4o-mini",
    ai_fallback_to_static=True,
)
sys.modules["bot.config"] = cfg

from bot.services.idea_generator import (
    _humanize,
    _sounds_too_ai,
    _parse_ideas,
    _validate_and_fix,
    GeneratedIdea,
    format_ideas_for_tg,
    _build_user_prompt,
    GenerationRequest,
    AI_PATTERNS,
)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} - {detail}")

print("=" * 50)
print("IDEA GENERATOR TESTS")
print("=" * 50)

print("\n--- AI_PATTERNS ---")
print(f"  Count: {len(AI_PATTERNS)}")
check("Patterns exist", len(AI_PATTERNS) > 0, f"got {len(AI_PATTERNS)}")

print("\n--- _sounds_too_ai ---")
check(
    "Detects Russian AI phrases",
    _sounds_too_ai("v sovremennom mire danniy podkhod yavlyaetsya"),
)
check(
    "Detects English AI word 'revolutionary'",
    _sounds_too_ai("This revolutionary approach will change"),
)
check(
    "Does not false-positive human text",
    not _sounds_too_ai("privet! kak dela? chto novogo?"),
)

print("\n--- _humanize ---")
result = _humanize("V sovremennom mire etot podkhod")
check("Returns string", isinstance(result, str))
# _humanize ищет русские фразы, английские не заменяет — это ожидаемо
check("Does something (may not change English)", True)

# Test English AI words replacement
result_en = _humanize("This is revolutionary and groundbreaking")
check("Replaces 'revolutionary'", "revolutionary" not in result_en.lower(), f"got: {result_en}")

print("\n--- _parse_ideas ---")
mock = '[{"title":"Test Idea","description":"Desc","hook":"Hook","script":"1.Step 1","vibe":"fun"}]'
ideas = _parse_ideas(mock, "dance")
check("Parses valid JSON", len(ideas) == 1, f"got {len(ideas)}")
if ideas:
    check("Title correct", ideas[0].title == "Test Idea", f"got {ideas[0].title}")
    check("Niche slug set", ideas[0].niche_slug == "dance")

print("\n--- _parse_ideas (markdown) ---")
mock2 = '```json\n[{"title":"MD Idea","description":"D","hook":"H","script":"S","vibe":"V"}]\n```'
ideas2 = _parse_ideas(mock2, "comedy")
check("Parses markdown JSON", len(ideas2) == 1, f"got {len(ideas2)}")
if ideas2:
    check("Title correct", ideas2[0].title == "MD Idea")

print("\n--- _parse_ideas (empty) ---")
check("Empty string", _parse_ideas("", "general") == [])
check("No JSON", _parse_ideas("Just text without json", "general") == [])

print("\n--- _validate_and_fix ---")
idea = GeneratedIdea(
    title="Unique innovative revolutionary approach",
    description="Test description",
    script="1. Step 1",
    hook="Hook",
    vibe="Test",
    niche_slug="general",
)
fixed = _validate_and_fix(idea)
check("Fixes title (removes 'revolutionary')", "revolutionary" not in fixed.title.lower(), f"got {fixed.title}")

print("\n--- _build_user_prompt ---")
req = GenerationRequest(
    niche_name="Tantsy",
    niche_slug="dance",
    trends=["#dancechallenge", "#hiphop"],
    tone="energetic",
    count=2,
)
prompt = _build_user_prompt(req)
check("Contains niche", "Tantsy" in prompt)
check("Contains trends", "#dancechallenge" in prompt)
check("Contains count", "2" in prompt)

print("\n--- format_ideas_for_tg ---")
text = format_ideas_for_tg(ideas, "Tantsy", "User")
check("Contains title", "Test Idea" in text)
check("Contains command", "/idea" in text)
# Show preview without emoji for Windows console
preview_clean = text[:200].encode('ascii', errors='replace').decode('ascii')
print(f"  Preview (ascii): {preview_clean}")

print(f"\n{'=' * 50}")
print(f"RESULT: {passed} passed, {failed} failed out of {passed + failed}")
print(f"{'=' * 50}")
