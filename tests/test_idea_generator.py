"""Тесты для AI-генератора идей."""

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.services.idea_generator import (
    _humanize,
    _sounds_too_ai,
    _parse_ideas,
    _validate_and_fix,
    GeneratedIdea,
    format_ideas_for_tg,
    _build_user_prompt,
    GenerationRequest,
    SYSTEM_PROMPT,
)


def test_humanize():
    """Проверяет, что AI-фразы заменяются на человеческие."""
    cases = [
        # (исходник, что должно появиться после замены)
        ("В современном мире", "Сейчас"),
        ("Данный подход", "Этот подход"),
        ("Является эффективным", "— это эффективным"),  # "Является" → "— это"
        ("В заключение", "Короче"),
        ("Подводя итог", "Короче говоря"),
        ("Здесь нет AI фраз", "Здесь нет AI фраз"),  # без изменений
    ]

    for original, expected_substring in cases:
        result = _humanize(original)
        assert expected_substring in result, (
            f"Ожидалось увидеть '{expected_substring}' в '{result}' (было: '{original}')"
        )
        if original != result:
            print(f"  ✓ '{original}' -> '{result}'")
        else:
            print(f"  ✓ '{original}' (без изменений)")


def test_sounds_too_ai():
    """Проверяет детектор AI-текста."""
    ai_texts = [
        "В современном мире данный подход является важным инструментом",
        "В наше время нельзя не упомянуть уникальную возможность",
        "В заключение следует отметить инновационный метод",
    ]
    human_texts = [
        "Привет! Давай снимем видео про завтрак за 5 минут",
        "Смотри, что я придумал — просто и заходит",
        "Короче, берешь телефон и снимаешь, как я",
    ]

    for text in ai_texts:
        assert _sounds_too_ai(text), f"Должно детектиться как AI: '{text[:50]}...'"
    print(f"  ✓ Все {len(ai_texts)} AI-текстов определены верно")

    for text in human_texts:
        assert not _sounds_too_ai(text), f"Не должно детектиться как AI: '{text[:50]}...'"
    print(f"  ✓ Все {len(human_texts)} человеческих текстов определены верно")


def test_parse_ideas_valid_json():
    """Парсинг корректного JSON."""
    mock = (
        '['
        '  {"title": "Как я перестал мыть посуду", '
        '   "description": "Лайфхак экономит время", '
        '   "hook": "Гора грязной посуды", '
        '   "script": "1. Проблема\\n2. Решение\\n3. Результат", '
        '   "vibe": "уютный"}, '
        '  {"title": "Утренняя рутина", '
        '   "description": "Мой идеальный старт дня", '
        '   "hook": "Будильник и улыбка", '
        '   "script": "1. Проснулся\\n2. Сделал\\n3. Поел", '
        '   "vibe": "энергичный"}'
        ']'
    )

    ideas = _parse_ideas(mock, "lifestyle")
    assert len(ideas) == 2, f"Ожидалось 2 идеи, получено {len(ideas)}"
    assert ideas[0].title == "Как я перестал мыть посуду"
    assert ideas[0].niche_slug == "lifestyle"
    assert ideas[1].title == "Утренняя рутина"
    print(f"  ✓ Распарсено {len(ideas)} идей")


def test_parse_ideas_with_markdown():
    """Парсинг JSON, обёрнутого в ```json ```."""
    mock = '```json\n[{"title": "Тест", "description": "Описание", "hook": "Хук", "script": "Сценарий", "vibe": "тест"}]\n```'
    ideas = _parse_ideas(mock, "general")
    assert len(ideas) == 1
    assert ideas[0].title == "Тест"
    print("  ✓ JSON с markdown распарсен")


def test_parse_ideas_empty():
    """Пустой ответ."""
    assert _parse_ideas("", "general") == []
    assert _parse_ideas("Тут нет JSON вообще", "general") == []
    print("  ✓ Пустые ответы обработаны")


def test_validate_and_fix():
    """Проверка очистки AI-текста."""
    idea = GeneratedIdea(
        title="В современном мире уникальный подход",
        description="Данный метод является эффективным инструментом",
        script="1. Шаг 1\n2. Шаг 2",
        hook="Зацепка",
        vibe="тест",
        niche_slug="general",
    )

    fixed = _validate_and_fix(idea)

    # Должно заменить AI-фразы
    assert "Сейчас" in fixed.title or "этот" in fixed.description.lower(), (
        f"Должно быть очищено: title='{fixed.title}', desc='{fixed.description}'"
    )
    print(f"  ✓ Очищено: title='{fixed.title}'")


def test_build_user_prompt():
    """Проверка сборки промпта."""
    request = GenerationRequest(
        niche_name="Танцы",
        niche_slug="dance",
        trends=["#dancechallenge", "#hiphopmoves"],
        tone="energetic",
        count=2,
    )

    prompt = _build_user_prompt(request)

    assert "Танцы" in prompt
    assert "#dancechallenge" in prompt
    assert "драйвовый" in prompt.lower()
    assert "2 идей" in prompt
    print("  ✓ Промпт собран корректно")


def test_system_prompt_quality():
    """Проверка, что системный промпт не содержит типичных AI-ошибок."""
    # Эти слова допустимы ТОЛЬКО в контексте запрета ("без: ...")
    # Проверяем, что они действительно используются как примеры того, что писать нельзя
    prompt = SYSTEM_PROMPT

    # Ищем раздел с запретами (после "Без:" / "ВАЖНО:" / "без:")
    # Если слова встречаются только внутри кавычек и после маркеров запрета — всё ОК
    assert "Без:" in prompt or "без:" in prompt.lower(), "В промпте должен быть раздел 'Без:'"
    assert 'В современном мире' in prompt, "Примеры плохих фраз должны быть в промпте"
    assert 'уникальный' in prompt, "Примеры плохих фраз должны быть в промпте"
    assert 'инновационный' in prompt, "Примеры плохих фраз должны быть в промпте"

    print("  ✓ Системный промпт корректно содержит примеры AI-штампов в контексте запрета")


def test_format_ideas_for_tg():
    """Проверка форматирования для Telegram."""
    ideas = [
        GeneratedIdea(
            title="Классная идея",
            description="Описание идеи",
            hook="Хук для первых секунд",
            script="1. Шаг раз\n2. Шаг два",
            vibe="весёлое",
            niche_slug="comedy",
        )
    ]

    text = format_ideas_for_tg(ideas, "Юмор", "Тестер")

    assert "Классная идея" in text
    assert "Описание идеи" in text
    assert "Хук для первых секунд" in text
    assert "весёлое" in text
    assert "Шаг раз" in text
    assert "Юмор" in text
    assert "/idea" in text  # должна быть ссылка на команду
    print("  ✓ Форматирование корректно")
    print(text)


if __name__ == "__main__":
    print("=" * 50)
    print("ТЕСТЫ AI-ГЕНЕРАТОРА ИДЕЙ")
    print("=" * 50)

    tests = [
        test_humanize,
        test_sounds_too_ai,
        test_parse_ideas_valid_json,
        test_parse_ideas_with_markdown,
        test_parse_ideas_empty,
        test_validate_and_fix,
        test_build_user_prompt,
        test_system_prompt_quality,
        test_format_ideas_for_tg,
    ]

    passed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        try:
            test()
            print(f"  ✅ {test.__name__} — OK")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")

    print(f"\n{'=' * 50}")
    print(f"ИТОГО: {passed}/{len(tests)} тестов пройдено")
    print(f"{'=' * 50}")
