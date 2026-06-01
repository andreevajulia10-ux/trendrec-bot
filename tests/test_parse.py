"""Простой тест парсинга."""
import sys
sys.path.insert(0, '.')
from bot.services.idea_generator import _parse_ideas, _sounds_too_ai, _humanize

# Test 1: _sounds_too_ai
print("=== _sounds_too_ai ===")
ai = _sounds_too_ai("v sovremennom mire danniy podkhod yavlyaetsya")
print("AI text:", ai, "(expected True)")
human = _sounds_too_ai("privet! kak dela?")
print("Human:", human, "(expected False)")

# Test 2: _humanize
print("\n=== _humanize ===")
r = _humanize("В современном мире данный подход является эффективным")
print("Result:", r)
print("Contains 'Сейчас':", "Сейчас" in r)
print("Contains 'Этот':", "Этот" in r)

# Test 3: _parse_ideas - with valid JSON
print("\n=== _parse_ideas (valid JSON) ===")
mock = '[{"title": "Test Idea", "description": "Test desc", "hook": "Test hook", "script": "1. Step 1\\n2. Step 2", "vibe": "fun"}]'
ideas = _parse_ideas(mock, 'dance')
print("Count:", len(ideas))
for idea in ideas:
    print(f"  Title: {idea.title}")
    print(f"  Script: {idea.script}")

# Test 4: _parse_ideas - with markdown
print("\n=== _parse_ideas (markdown JSON) ===")
mock2 = '```json\n[{"title": "Markdown Idea", "description": "Desc", "hook": "Hook", "script": "Steps", "vibe": "cool"}]\n```'
ideas2 = _parse_ideas(mock2, 'comedy')
print("Count:", len(ideas2))
for idea in ideas2:
    print(f"  Title: {idea.title}")

print("\nALL TESTS PASSED")
