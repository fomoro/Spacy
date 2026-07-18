"""Base de utilidades para los validadores de recursos JSON."""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "resources"

CONVERSATION_PATHS = {
    "carlos.json": RESOURCES / "corpus" / "conversations" / "carlos.json",
    "diego.json": RESOURCES / "corpus" / "conversations" / "diego.json",
}

RESOURCE_PATHS = {
    "intents_and_subintents.json": (
        ROOT / "src" / "domain" / "resources" / "intents_and_subintents.json"
    ),
    "text_normalizer_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json",
    "matcher_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json",
    "lemma_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json",
    "entity_ruler_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json",
    "linguistic_evidence_mapping.json": (
        ROOT / "src" / "application" / "resources" / "linguistic_evidence_mapping.json"
    ),
    "conversation_action_rules.json": (
        ROOT / "src" / "domain" / "resources" / "conversation_action_rules.json"
    ),
    "response_templates.json": (
        ROOT / "src" / "application" / "resources" / "response_templates.json"
    ),
    "phrase_matcher_service_config.json": (
        ROOT / "src" / "infrastructure" / "resources" / "phrase_matcher_service_config.json"
    ),
    "conversation_profiles.json": RESOURCES / "corpus" / "profiles" / "conversation_profiles.json",
}

def load(name: str) -> dict[str, Any]:
    data = json.loads(RESOURCE_PATHS[name].read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{name}: la raíz debe ser un objeto JSON.")
    return data

def taxonomy_pairs(taxonomy: dict[str, Any]) -> set[str]:
    return {
        f"{intent_id}.{subintent_id}"
        for intent_id, intent in taxonomy.get("intents", {}).items()
        for subintent_id in intent.get("subintents", {})
    }

def evidence_pair(item: dict[str, Any]) -> str:
    return f"{item['intent']}.{item['subintent']}"
