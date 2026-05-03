"""Tests for suggestion prompt localization helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(name: str):
    path = Path(__file__).resolve().parents[1] / "custom_components" / "ai_automation_suggester" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


language_utils = load_module("language_utils")


def test_language_name_normalizes_home_assistant_locale_codes():
    assert language_utils.language_name("it") == "Italian"
    assert language_utils.language_name("pt_BR") == "Portuguese"
    assert language_utils.language_name("cs-CZ") == "Czech"


def test_suggestion_language_instruction_skips_english_and_empty_values():
    assert language_utils.suggestion_language_instruction(None) == ""
    assert language_utils.suggestion_language_instruction("en") == ""


def test_suggestion_language_instruction_preserves_yaml_identifiers():
    instruction = language_utils.suggestion_language_instruction("it")

    assert "Italian" in instruction
    assert "Keep YAML" in instruction
    assert "entity_ids" in instruction