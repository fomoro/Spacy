"""Valida la coherencia cruzada de los recursos declarativos del motor."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESOURCES = ROOT / "resources"
BENCHMARK_JSON = RESOURCES / "corpus" / "benchmarks" / "customer_intent_benchmark.json"
CONVERSATION_PATHS = {
    "carlos.json": RESOURCES / "corpus" / "conversations" / "carlos.json",
    "diego.json": RESOURCES / "corpus" / "conversations" / "diego.json",
}
RESOURCE_PATHS = {
    "intents_and_subintents.json": (
        ROOT / "src" / "temp" / "resources" / "intent_resolver" / "intents_and_subintents.json"
    ),
    "text_normalizer_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json",
    "matcher_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json",
    "lemma_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json",
    "entity_ruler_service_config.json": ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json",
    "linguistic_evidence_mapping.json": (
        ROOT / "src" / "temp" / "resources" / "intent_resolver" / "linguistic_evidence_mapping.json"
    ),
    "conversation_action_rules.json": (
        ROOT / "src" / "temp" / "resources" / "intent_resolver" / "conversation_action_rules.json"
    ),
    "response_templates.json": ROOT / "src" / "temp" / "resources" / "response_templates.json",
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
        for intent_id, intent in taxonomy["intents"].items()
        for subintent_id in intent["subintents"]
    }


def evidence_pair(item: dict[str, Any]) -> str:
    return f"{item['intent']}.{item['subintent']}"


def validate() -> list[str]:
    errors: list[str] = []
    missing = [name for name, path in RESOURCE_PATHS.items() if not path.is_file()]
    missing.extend(
        name for name, path in CONVERSATION_PATHS.items() if not path.is_file()
    )
    if missing:
        return [f"Faltan recursos: {', '.join(missing)}"]

    taxonomy = load("intents_and_subintents.json")
    menu = load("phrase_matcher_service_config.json")
    normalizer = load("text_normalizer_service_config.json")
    matcher = load("matcher_service_config.json")
    lemmas = load("lemma_service_config.json")
    ruler = load("entity_ruler_service_config.json")
    evidence_mapping = load("linguistic_evidence_mapping.json")
    conversation_rules = load("conversation_action_rules.json")
    response_templates = load("response_templates.json")
    profiles = load("conversation_profiles.json")
    valid_pairs = taxonomy_pairs(taxonomy)
    covered_pairs: set[str] = set()

    expected_evidence_mapping_fields = {
        "metadata",
        "matcher_signals",
        "lemma_signals",
        "phrase_entity_types",
        "service_entities",
        "entity_ruler_types",
    }
    if set(evidence_mapping) != expected_evidence_mapping_fields:
        errors.append(
            "linguistic_evidence_mapping.json: solo debe contener evidencia "
            "lingüística; no campos, preguntas ni acciones conversacionales."
        )

    conversation_messages: set[str] = set()
    for conversation_name, conversation_path in CONVERSATION_PATHS.items():
        conversation = json.loads(conversation_path.read_text(encoding="utf-8"))
        if not isinstance(conversation, list) or len(conversation) != 5:
            errors.append(
                f"Conversación {conversation_name}: debe ser una lista de cinco mensajes."
            )
            continue
        if not all(isinstance(message, str) and message.strip() for message in conversation):
            errors.append(
                f"Conversación {conversation_name}: todos los elementos deben ser textos no vacíos."
            )
            continue
        normalized = {" ".join(message.casefold().split()) for message in conversation}
        if len(normalized) != 5:
            errors.append(f"Conversación {conversation_name}: contiene mensajes duplicados.")
        overlap = conversation_messages.intersection(normalized)
        if overlap:
            errors.append(
                f"Conversación {conversation_name}: repite mensajes de otro flujo."
            )
        conversation_messages.update(normalized)

    taxonomy_metadata = taxonomy.get("metadata", {})
    expected_taxonomy_metadata = {
        "schema_version",
        "purpose",
        "language",
        "intent_count",
        "intent_subintent_pair_count",
        "slot_count",
    }
    if not isinstance(taxonomy_metadata, dict) or set(taxonomy_metadata) != expected_taxonomy_metadata:
        errors.append(
            "intents_and_subintents.json: metadata no coincide con el contrato mínimo."
        )
    else:
        if taxonomy_metadata.get("intent_count") != len(taxonomy.get("intents", {})):
            errors.append("intents_and_subintents.json: intent_count es incorrecto.")
        if taxonomy_metadata.get("intent_subintent_pair_count") != len(valid_pairs):
            errors.append(
                "intents_and_subintents.json: intent_subintent_pair_count es incorrecto."
            )
    for intent_id, intent in taxonomy.get("intents", {}).items():
        if not str(intent.get("description", "")).strip():
            errors.append(
                f"intents_and_subintents.json: '{intent_id}' requiere descripción."
            )
        for subintent_id, description in intent.get("subintents", {}).items():
            if not isinstance(description, str) or not description.strip():
                errors.append(
                    "intents_and_subintents.json: "
                    f"'{intent_id}.{subintent_id}' requiere descripción."
                )

    configuration_metadata_fields = {"schema_version", "purpose", "language"}
    for resource_name, resource in (
        ("matcher_service_config.json", matcher),
        ("lemma_service_config.json", lemmas),
        ("linguistic_evidence_mapping.json", evidence_mapping),
    ):
        metadata = resource.get("metadata", {})
        if (
            not isinstance(metadata, dict)
            or set(metadata) != configuration_metadata_fields
        ):
            errors.append(
                f"{resource_name}: metadata no coincide con el contrato mínimo."
            )
        elif not str(metadata.get("purpose", "")).strip():
            errors.append(f"{resource_name}: metadata.purpose debe ser texto no vacío.")

    if not isinstance(normalizer.get("options"), dict):
        errors.append("text_normalizer_service_config.json: falta 'options'.")
    lemma_options = lemmas.get("options", {})
    if not isinstance(lemma_options, dict) or set(lemma_options) != {
        "minimum_token_length",
        "ignored_pos",
    }:
        errors.append("lemma_service_config.json: options no coincide con el contrato.")
    else:
        if not isinstance(lemma_options.get("minimum_token_length"), int):
            errors.append(
                "lemma_service_config.json: options.minimum_token_length debe ser entero."
            )
        ignored_pos = lemma_options.get("ignored_pos")
        if not isinstance(ignored_pos, list) or not all(
            isinstance(value, str) and value for value in ignored_pos
        ):
            errors.append(
                "lemma_service_config.json: options.ignored_pos debe ser una lista de textos."
            )

    pattern_ids: set[str] = set()
    for pattern in matcher.get("patterns", []):
        rule_id = str(pattern.get("id", ""))
        if not rule_id:
            errors.append("matcher_service_config.json: hay una regla sin id.")
        elif rule_id in pattern_ids:
            errors.append(f"Matcher: id duplicado '{rule_id}'.")
        pattern_ids.add(rule_id)
        if set(pattern) - {"id", "pattern", "full_text_only"}:
            errors.append(
                f"Matcher: '{rule_id}' contiene decisiones que no pertenecen a infraestructura."
            )
        serialized_pattern = json.dumps(pattern.get("pattern"), ensure_ascii=False)
        if "ENT_TYPE" in serialized_pattern or "ENT_ID" in serialized_pattern:
            errors.append(f"Matcher: '{rule_id}' todavía depende de entidades previas.")

    matcher_mappings = evidence_mapping.get("matcher_signals", {})
    if set(matcher_mappings) != pattern_ids:
        errors.append(
            "Mapeo de evidencia: las señales Matcher no coinciden con sus patrones."
        )
    for rule_id, evidence in matcher_mappings.items():
        pair = evidence_pair(evidence)
        covered_pairs.add(pair)
        if pair not in valid_pairs:
            errors.append(
                f"Mapeo Matcher: '{rule_id}' referencia '{pair}' fuera de la taxonomía."
            )

    lemma_ids: set[str] = set()
    for signal in lemmas.get("signals", []):
        lemma_id = str(signal.get("lemma", ""))
        lemma_ids.add(lemma_id)
        if set(signal) != {"lemma", "forms"}:
            errors.append(
                f"Lemma: '{lemma_id}' contiene decisiones que no pertenecen a infraestructura."
            )
    lemma_mappings = evidence_mapping.get("lemma_signals", {})
    if set(lemma_mappings) != lemma_ids:
        errors.append("Mapeo de evidencia: las señales Lemma no coinciden con su catálogo.")
    for lemma_id, mappings in lemma_mappings.items():
        for evidence in mappings:
            pair = evidence_pair(evidence)
            covered_pairs.add(pair)
            if pair not in valid_pairs:
                errors.append(
                    f"Mapeo Lemma: '{lemma_id}' referencia '{pair}' fuera de la taxonomía."
                )

    mapped_entity_evidence: list[dict[str, Any]] = []
    for mapping_name in ("phrase_entity_types", "entity_ruler_types"):
        for items in evidence_mapping.get(mapping_name, {}).values():
            mapped_entity_evidence.extend(items)
    mapped_entity_evidence.extend(
        evidence_mapping.get("service_entities", {}).values()
    )
    for evidence in mapped_entity_evidence:
        pair = evidence_pair(evidence)
        covered_pairs.add(pair)
        if pair not in valid_pairs:
            errors.append(f"Mapeo de entidades referencia '{pair}' fuera de la taxonomía.")
    resolver_settings = taxonomy.get("resolver_settings", {})
    thresholds = resolver_settings.get("thresholds", {})
    multipliers = resolver_settings.get("source_multipliers", {})
    if set(resolver_settings) != {"thresholds", "source_multipliers"}:
        errors.append(
            "intents_and_subintents.json: resolver_settings no coincide con el contrato."
        )
    if set(thresholds) != {
        "minimum_score",
        "clarification_margin",
        "maximum_confidence",
    }:
        errors.append(
            "intents_and_subintents.json: thresholds no coincide con el contrato."
        )
    if set(multipliers) != {
        "matcher",
        "lemma_spacy",
        "lemma_catalog_fallback",
        "lemma_surface",
        "phrase_matcher",
        "entity_ruler",
    }:
        errors.append(
            "intents_and_subintents.json: source_multipliers no coincide con el contrato."
        )
    for intent_id, intent in taxonomy.get("intents", {}).items():
        priority = intent.get("tie_break_priority")
        if not isinstance(priority, int) or isinstance(priority, bool):
            errors.append(
                f"intents_and_subintents.json: '{intent_id}' requiere tie_break_priority entero."
            )

    for legacy_key in (
        "required_entities",
        "clarification_messages",
        "phrase_evidence",
        "service_entity_map",
        "entity_ruler_evidence",
    ):
        if legacy_key in taxonomy:
            errors.append(
                f"Resolver: '{legacy_key}' pertenece a otro recurso de aplicación."
            )

    actions = conversation_rules.get("conversation_actions", {})
    slots = taxonomy.get("slots", {})
    rules = conversation_rules.get("rules_by_intent_and_subintent", {})
    questions = conversation_rules.get("questions", {})
    
    if taxonomy_metadata.get("slot_count") != len(slots):
        errors.append(
            f"intents_and_subintents.json: metadata.slot_count debe ser {len(slots)}."
        )
    conversation_metadata = conversation_rules.get("metadata", {})
    expected_conversation_metadata_fields = {
        "schema_version",
        "purpose",
        "language",
        "conversation_action_count",
        "intent_subintent_rule_count",
        "question_count",
    }
    if (
        not isinstance(conversation_metadata, dict)
        or set(conversation_metadata) != expected_conversation_metadata_fields
    ):
        errors.append(
            "conversation_action_rules.json: metadata no coincide con el contrato mínimo."
        )
    else:
        if not str(conversation_metadata.get("purpose", "")).strip():
            errors.append(
                "conversation_action_rules.json: metadata.purpose debe ser texto no vacío."
            )
        expected_counts = {
            "conversation_action_count": len(actions),
            "intent_subintent_rule_count": len(rules),
            "question_count": len(questions),
        }
        for count_field, expected_count in expected_counts.items():
            if conversation_metadata.get(count_field) != expected_count:
                errors.append(
                    "conversation_action_rules.json: "
                    f"metadata.{count_field} debe ser {expected_count}."
                )
    for field, value in (
        ("conversation_actions", actions),
        ("rules_by_intent_and_subintent", rules),
        ("questions", questions),
    ):
        if not isinstance(value, dict) or not value:
            errors.append(f"Acciones conversacionales: '{field}' debe ser un objeto no vacío.")

    expected_action_categories = {
        "resolved": "successful_resolution",
        "needs_user_clarification": "clarification",
        "needs_transaction_confirmation": "confirmation",
        "needs_business_lookup": "operational_lookup",
        "needs_human_safety_validation": "safety_escalation",
        "needs_human_assistance": "human_escalation",
        "needs_identity_verification": "identity_verification",
        "out_of_scope": "terminal_result",
    }
    if set(actions) != set(expected_action_categories):
        errors.append("Acciones conversacionales: el catálogo no coincide con el contrato.")
    for action_id, expected_category in expected_action_categories.items():
        action = actions.get(action_id, {})
        if not isinstance(action, dict):
            errors.append(f"Acciones conversacionales: '{action_id}' debe ser un objeto.")
            continue
        if set(action) != {"category", "requires_clarification_compat", "description"}:
            errors.append(
                f"Acciones conversacionales: '{action_id}' contiene campos inesperados."
            )
        if action.get("category") != expected_category:
            errors.append(
                f"Acciones conversacionales: categoría incorrecta en '{action_id}'."
            )
        if not isinstance(action.get("requires_clarification_compat"), bool):
            errors.append(
                f"Acciones conversacionales: '{action_id}' requiere compatibilidad booleana."
            )
        if not str(action.get("description", "")).strip():
            errors.append(
                f"Acciones conversacionales: '{action_id}' requiere una descripción."
            )

    if not isinstance(slots, dict) or not slots:
        errors.append("Slots: 'slots' debe ser un objeto no vacío.")
        slots = {}
    else:
        valid_slot_fields = {"description", "classification"}
        valid_classifications = {
            "operational", "personal_data", "sensitive_personal_data",
            "financial_data", "linked_identifier", "tax_data",
        }
        for slot_id, definition in slots.items():
            if not isinstance(definition, dict):
                errors.append(f"Slots: '{slot_id}' debe ser un objeto.")
                continue
            unexpected_fields = set(definition) - valid_slot_fields
            if unexpected_fields:
                errors.append(
                    f"Slots: '{slot_id}' contiene campos desconocidos: "
                    + ", ".join(sorted(unexpected_fields))
                )
            if not str(definition.get("description", "")).strip():
                errors.append(f"Slots: '{slot_id}' requiere una descripción.")
            classification = definition.get("classification")
            if classification not in valid_classifications:
                errors.append(
                    f"Slots: '{slot_id}' usa clasificación desconocida '{classification}'."
                )
    allowed_placeholders = set(slots) | {"options"}
    for question_key, question in questions.items():
        if not isinstance(question, dict) or not str(question.get("template", "")).strip():
            errors.append(f"Acciones conversacionales: pregunta '{question_key}' sin template.")
            continue
        for text_field in ("template", "fallback"):
            text = question.get(text_field)
            if text is None:
                continue
            try:
                placeholders = {
                    name for _, name, _, _ in Formatter().parse(str(text)) if name
                }
            except ValueError as exc:
                errors.append(
                    f"Acciones conversacionales: formato inválido en '{question_key}': {exc}."
                )
                continue
            unknown = placeholders - allowed_placeholders
            if unknown:
                errors.append(
                    f"Acciones conversacionales: '{question_key}' usa slots desconocidos: "
                    + ", ".join(sorted(unknown))
                )

    expected_response_fields = {
        "metadata",
        "fallback_template",
        "templates",
        "direct_response_by_intent_and_subintent",
    }
    if set(response_templates) != expected_response_fields:
        errors.append(
            "response_templates.json: la raíz no coincide con el contrato de respuestas."
        )

    templates = response_templates.get("templates", {})
    direct_responses = response_templates.get(
        "direct_response_by_intent_and_subintent", {}
    )
    fallback_template = response_templates.get("fallback_template")
    response_metadata = response_templates.get("metadata", {})
    expected_response_metadata_fields = {
        "schema_version",
        "purpose",
        "language",
        "template_count",
        "direct_response_pair_count",
    }
    if (
        not isinstance(response_metadata, dict)
        or set(response_metadata) != expected_response_metadata_fields
    ):
        errors.append(
            "response_templates.json: metadata no coincide con el contrato."
        )
    else:
        if not str(response_metadata.get("purpose", "")).strip():
            errors.append("response_templates.json: metadata.purpose está vacío.")
        if response_metadata.get("language") != "es-CO":
            errors.append("response_templates.json: metadata.language debe ser 'es-CO'.")
        if response_metadata.get("template_count") != len(templates):
            errors.append(
                "response_templates.json: metadata.template_count no coincide."
            )
        if response_metadata.get("direct_response_pair_count") != len(
            direct_responses
        ):
            errors.append(
                "response_templates.json: metadata.direct_response_pair_count "
                "no coincide."
            )

    if not isinstance(templates, dict) or not templates:
        errors.append("Respuestas: 'templates' debe ser un objeto no vacío.")
        templates = {}
    else:
        for template_key, definition in templates.items():
            if not isinstance(definition, dict) or set(definition) != {
                "template",
                "required_values",
                "fallback",
            }:
                errors.append(
                    f"Respuestas: template '{template_key}' no coincide con el contrato."
                )
                continue
            template = definition.get("template")
            fallback = definition.get("fallback")
            required_values = definition.get("required_values")
            if not isinstance(template, str) or not template.strip():
                errors.append(
                    f"Respuestas: template '{template_key}' debe ser texto no vacío."
                )
                continue
            if not isinstance(fallback, str) or not fallback.strip():
                errors.append(
                    f"Respuestas: fallback '{template_key}' debe ser texto no vacío."
                )
                continue
            if not isinstance(required_values, list) or not all(
                isinstance(value, str) and value for value in required_values
            ):
                errors.append(
                    f"Respuestas: '{template_key}' tiene required_values inválido."
                )
                continue
            if len(required_values) != len(set(required_values)):
                errors.append(
                    f"Respuestas: '{template_key}' repite required_values."
                )
            try:
                placeholders = {
                    name for _, name, _, _ in Formatter().parse(template) if name
                }
                fallback_placeholders = {
                    name for _, name, _, _ in Formatter().parse(fallback) if name
                }
            except ValueError as exc:
                errors.append(
                    f"Respuestas: formato inválido en '{template_key}': {exc}."
                )
                continue
            if placeholders != set(required_values):
                errors.append(
                    f"Respuestas: '{template_key}' no sincroniza placeholders "
                    "y required_values."
                )
            if fallback_placeholders:
                errors.append(
                    f"Respuestas: fallback '{template_key}' no debe requerir valores."
                )

    if fallback_template not in templates:
        errors.append("Respuestas: fallback_template referencia una plantilla inexistente.")

    if not isinstance(direct_responses, dict):
        errors.append(
            "Respuestas: direct_response_by_intent_and_subintent debe ser un objeto."
        )
        direct_responses = {}
    expected_direct_pairs = {
        pair
        for pair in valid_pairs
        if not isinstance(rules.get(pair), dict)
        or not rules[pair].get("on_complete")
    }
    if set(direct_responses) != expected_direct_pairs:
        missing_direct = sorted(expected_direct_pairs - set(direct_responses))
        unexpected_direct = sorted(set(direct_responses) - expected_direct_pairs)
        if missing_direct:
            errors.append(
                "Respuestas: faltan respuestas directas para "
                + ", ".join(missing_direct)
            )
        if unexpected_direct:
            errors.append(
                "Respuestas: hay respuestas directas para pares que producen una acción: "
                + ", ".join(unexpected_direct)
            )
    for pair, template_key in direct_responses.items():
        if pair not in valid_pairs:
            errors.append(f"Respuestas: pareja desconocida '{pair}'.")
        if template_key not in templates:
            errors.append(
                f"Respuestas: '{pair}' referencia template desconocido '{template_key}'."
            )
    referenced_templates = set(direct_responses.values()) | {fallback_template}
    unused_templates = sorted(set(templates) - referenced_templates)
    if unused_templates:
        errors.append(
            "Respuestas: templates sin uso: " + ", ".join(unused_templates)
        )

    for pair, policy in rules.items():
        if pair not in valid_pairs:
            errors.append(
                f"Acciones conversacionales: regla '{pair}' fuera de la taxonomía."
            )
        if not isinstance(policy, dict):
            errors.append(f"Acciones conversacionales: regla '{pair}' debe ser un objeto.")
            continue
        required = [str(slot) for slot in policy.get("required_slots", [])]
        required_any = [
            [str(slot) for slot in group]
            for group in policy.get("required_any", [])
        ]
        referenced_slots = set(required)
        for group in required_any:
            referenced_slots.update(group)
        unknown_slots = referenced_slots - set(slots)
        if unknown_slots:
            errors.append(
                f"Acciones conversacionales {pair}: slots desconocidos: "
                + ", ".join(sorted(unknown_slots))
            )
        for mode_field in ("on_missing", "on_complete"):
            mode = policy.get(mode_field)
            if mode is not None and mode not in actions:
                errors.append(
                    f"Acciones conversacionales {pair}: acción desconocida '{mode}'."
                )
        question_by_slot = policy.get("question_by_slot", {})
        expected_question_slots = set(required) | {
            "|".join(group) for group in required_any if group
        }
        missing_question_slots = expected_question_slots - set(question_by_slot)
        if missing_question_slots:
            errors.append(
                f"Acciones conversacionales {pair}: faltan preguntas para "
                + ", ".join(sorted(missing_question_slots))
            )
        referenced_questions = list(question_by_slot.values())
        if policy.get("complete_question"):
            referenced_questions.append(policy["complete_question"])
        requires_identity = policy.get("requires_identity_verification")
        if requires_identity is not None and not isinstance(requires_identity, bool):
            errors.append(
                f"Acciones conversacionales {pair}: requires_identity_verification debe ser booleano."
            )
        if requires_identity is True:
            if "needs_identity_verification" not in actions:
                errors.append(
                    "Acciones conversacionales: falta declarar needs_identity_verification."
                )
            identity_question = policy.get("identity_question")
            if not identity_question:
                errors.append(
                    f"Acciones conversacionales {pair}: falta identity_question."
                )
            else:
                referenced_questions.append(identity_question)
        for question_key in referenced_questions:
            if question_key not in questions:
                errors.append(
                    f"Acciones conversacionales {pair}: pregunta desconocida '{question_key}'."
                )

    uncovered = sorted(valid_pairs - covered_pairs)
    if uncovered:
        errors.append(
            "Taxonomía sin ruta de evidencia declarada: " + ", ".join(uncovered)
        )

    menu_phrases: set[str] = set()
    product_ids: set[str] = set()
    for entity_type, group in menu.get("entity_types", {}).items():
        ids: set[str] = set()
        phrase_owner: dict[str, str] = {}
        for item in group.get("items", []):
            entity_id = str(item.get("id", ""))
            if entity_id in ids:
                errors.append(
                    f"Catálogo PhraseMatcher {entity_type}: id duplicado '{entity_id}'."
                )
            ids.add(entity_id)
            if entity_type in {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}:
                product_ids.add(entity_id)
            for raw_phrase in item.get("phrases", []):
                phrase = " ".join(str(raw_phrase).casefold().split())
                if not phrase:
                    errors.append(
                        f"Catálogo PhraseMatcher {entity_type}/{entity_id}: frase vacía."
                    )
                    continue
                previous = phrase_owner.get(phrase)
                if previous and previous != entity_id:
                    errors.append(
                        f"Catálogo PhraseMatcher {entity_type}: frase '{phrase}' "
                        f"pertenece a '{previous}' y '{entity_id}'."
                    )
                phrase_owner[phrase] = entity_id
                menu_phrases.add(phrase)

    ruler_keys: set[tuple[str, str]] = set()
    for pattern in ruler.get("patterns", []):
        raw = pattern.get("pattern")
        if not isinstance(raw, str):
            continue
        phrase = " ".join(raw.casefold().split())
        key = (str(pattern.get("label")), phrase)
        if key in ruler_keys:
            errors.append(f"EntityRuler: patrón duplicado {key}.")
        ruler_keys.add(key)
        if phrase in menu_phrases:
            errors.append(f"Propiedad ambigua: '{phrase}' aparece en menú y EntityRuler.")

    profile_items = profiles.get("profiles", [])
    if not isinstance(profile_items, list):
        errors.append("Perfiles: 'profiles' debe ser una lista.")
        profile_items = []
    declared_count = profiles.get("profile_count")
    if declared_count != 20 or len(profile_items) != 20:
        errors.append(
            f"Perfiles: se esperaban 20 perfiles; hay {len(profile_items)} "
            f"y profile_count declara {declared_count!r}."
        )
    if profiles.get("contains_cases") is not False:
        errors.append("Perfiles: 'contains_cases' debe ser false.")

    if not str(profiles.get("usage_note", "")).strip():
        errors.append("Perfiles: falta 'usage_note'.")

    profile_ids: set[str] = set()
    required_profile_lists = (
        "linguistic_features",
        "frequent_needs",
        "clarification_focus",
    )
    forbidden_profile_keys = {
        "age", "edad", "gender", "genero", "género", "ethnicity", "etnia",
        "religion", "religión", "socioeconomic_status", "estrato",
        "cases", "casos", "messages", "mensajes",
    }
    for profile in profile_items:
        if not isinstance(profile, dict):
            errors.append("Perfiles: cada elemento debe ser un objeto.")
            continue
        profile_id = str(profile.get("id", ""))
        if not profile_id:
            errors.append("Perfiles: existe un perfil sin id.")
        elif profile_id in profile_ids:
            errors.append(f"Perfiles: id duplicado '{profile_id}'.")
        profile_ids.add(profile_id)
        if not str(profile.get("name", "")).strip() or not str(profile.get("description", "")).strip():
            errors.append(f"Perfiles {profile_id}: requiere name y description.")
        for field in required_profile_lists:
            values = profile.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                errors.append(
                    f"Perfiles {profile_id}: '{field}' debe ser una lista no vacía de textos."
                )
        forbidden = forbidden_profile_keys.intersection(profile)
        if forbidden:
            errors.append(
                f"Perfiles {profile_id}: contiene atributos o casos no permitidos: "
                + ", ".join(sorted(forbidden))
            )

    if not BENCHMARK_JSON.is_file():
        errors.append("Benchmark: falta customer_intent_benchmark.json.")
    else:
        dataset = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
        dataset_cases = dataset.get("cases", []) if isinstance(dataset, dict) else []
        metadata = dataset.get("metadata", {}) if isinstance(dataset, dict) else {}
        if not isinstance(dataset, dict) or set(dataset) != {"metadata", "cases"}:
            errors.append("Dataset JSON: la raíz debe contener solo metadata y cases.")
        if not isinstance(dataset_cases, list):
            errors.append("Dataset JSON: 'cases' debe ser una lista.")
            dataset_cases = []
        expected_metadata_fields = {
            "schema_version",
            "purpose",
            "language",
            "case_count",
            "profile_count",
            "context_case_count",
            "intent_subintent_pair_count",
        }
        if set(metadata) != expected_metadata_fields:
            errors.append("Dataset: metadata no coincide con el contrato mínimo canónico.")
        if not str(metadata.get("purpose", "")).strip():
            errors.append("Dataset: metadata.purpose debe explicar el uso del benchmark.")
        if metadata.get("language") != "es-CO":
            errors.append("Dataset: metadata.language debe ser 'es-CO'.")
        if len(dataset_cases) != 600:
            errors.append(f"Dataset: se esperaban 600 casos; hay {len(dataset_cases)}.")

        canonical_profile_ids = {str(profile.get("id")) for profile in profile_items}
        dataset_ids: set[str] = set()
        normalized_messages: set[str] = set()
        cases_by_profile: dict[str, int] = {}
        contexts_by_profile: dict[str, int] = {}
        modes_by_profile: dict[str, set[str]] = {}
        pair_counts: dict[str, int] = {}
        dataset_pairs: set[str] = set()
        valid_modes = set(actions)
        required_benchmark_modes = {
            "resolved",
            "needs_transaction_confirmation",
            "needs_business_lookup",
            "needs_human_safety_validation",
        }
        information_gathering_modes = {
            "needs_user_clarification",
            "needs_identity_verification",
        }
        valid_question_keys = set(questions)
        menu_entity_ids = {
            entity_type: {
                str(item.get("id")) for item in group.get("items", [])
            }
            for entity_type, group in menu.get("entity_types", {}).items()
        }
        ruler_entity_ids: dict[str, set[str]] = {}
        for pattern in ruler.get("patterns", []):
            ruler_entity_ids.setdefault(str(pattern.get("label")), set()).add(
                str(pattern.get("id"))
            )

        for position, case in enumerate(dataset_cases, start=1):
            if not isinstance(case, dict):
                errors.append(f"Dataset: el caso en posición {position} no es un objeto.")
                continue
            expected_case_fields = {
                "id", "profile_id", "message", "context", "expected",
                "expected_entities",
            }
            if set(case) != expected_case_fields:
                errors.append(
                    f"Dataset: el caso en posición {position} no coincide con el esquema mínimo."
                )
            case_id = str(case.get("id", ""))
            expected_id = f"caso_{position:03d}"
            if case_id != expected_id:
                errors.append(f"Dataset: se esperaba id '{expected_id}' y apareció '{case_id}'.")
            if case_id in dataset_ids:
                errors.append(f"Dataset: id duplicado '{case_id}'.")
            dataset_ids.add(case_id)

            profile_id = str(case.get("profile_id", ""))
            if profile_id not in canonical_profile_ids:
                errors.append(f"Dataset {case_id}: perfil desconocido '{profile_id}'.")
            cases_by_profile[profile_id] = cases_by_profile.get(profile_id, 0) + 1

            context = case.get("context", {})
            allowed_context_keys = {
                "producto_activo", "pedido_activo", "pedido_anterior",
                "direccion_previa", "menu_enviado_previamente",
                "menu_pdf_ultima_fecha_envio",
                "budget", "delivery_zone", "customer_name", "phone",
                "order_id", "reservation_id", "invoice_data",
                "fulfillment_method",
                "identity_verified",
            }
            if not isinstance(context, dict):
                errors.append(f"Dataset {case_id}: context debe ser un objeto.")
                context = {}
            else:
                unknown_context_keys = set(context) - allowed_context_keys
                if unknown_context_keys:
                    errors.append(
                        f"Dataset {case_id}: claves de contexto desconocidas: "
                        + ", ".join(sorted(unknown_context_keys))
                    )
                if context:
                    contexts_by_profile[profile_id] = contexts_by_profile.get(profile_id, 0) + 1
                active_product = context.get("producto_activo")
                if active_product is not None and active_product not in product_ids:
                    errors.append(
                        f"Dataset {case_id}: producto_activo desconocido '{active_product}'."
                    )
                for boolean_key in (
                    "pedido_activo", "menu_enviado_previamente", "identity_verified"
                ):
                    if boolean_key in context and not isinstance(context[boolean_key], bool):
                        errors.append(
                            f"Dataset {case_id}: context.{boolean_key} debe ser booleano."
                        )
                menu_date = context.get("menu_pdf_ultima_fecha_envio")
                if menu_date is not None and not isinstance(menu_date, str):
                    errors.append(
                        f"Dataset {case_id}: menu_pdf_ultima_fecha_envio debe ser texto."
                    )

            raw_message = str(case.get("message", ""))
            message = " ".join(raw_message.casefold().split())
            if not message:
                errors.append(f"Dataset {case_id}: mensaje vacío.")
            elif message in normalized_messages:
                errors.append(f"Dataset {case_id}: mensaje duplicado '{message}'.")
            normalized_messages.add(message)

            expected = case.get("expected", {})
            expected_fields = {
                "intent", "subintent"
            }
            if not isinstance(expected, dict) or set(expected) != expected_fields:
                errors.append(f"Dataset {case_id}: expected no coincide con el esquema mínimo.")
                expected = expected if isinstance(expected, dict) else {}
            pair = f"{expected.get('intent')}.{expected.get('subintent')}"
            dataset_pairs.add(pair)
            if pair not in valid_pairs:
                errors.append(f"Dataset {case_id}: '{pair}' no existe en la taxonomía.")
            pair_counts[pair] = pair_counts.get(pair, 0) + 1



            for entity in case.get("expected_entities", []):
                entity_type = str(entity.get("entity_type", ""))
                entity_id = str(entity.get("entity_id", ""))
                if entity_type in menu_entity_ids and entity_id not in menu_entity_ids[entity_type]:
                    errors.append(
                        f"Dataset {case_id}: entidad desconocida {entity_type}:{entity_id}."
                    )
                elif entity_type in ruler_entity_ids and entity_id not in ruler_entity_ids[entity_type]:
                    errors.append(
                        f"Dataset {case_id}: entidad contextual desconocida {entity_type}:{entity_id}."
                    )
                elif entity_type not in menu_entity_ids and entity_type not in ruler_entity_ids and entity_type != "MONEY":
                    errors.append(f"Dataset {case_id}: tipo de entidad desconocido '{entity_type}'.")

        if set(cases_by_profile) != canonical_profile_ids:
            errors.append("Dataset: los perfiles no coinciden exactamente con conversation_profiles.json.")
        context_case_count = sum(contexts_by_profile.values())
        if context_case_count != 150:
            errors.append(
                f"Dataset: se esperaban 150 casos con contexto y hay "
                f"{context_case_count}."
            )
        expected_benchmark_counts = {
            "case_count": len(dataset_cases),
            "profile_count": len(canonical_profile_ids),
            "context_case_count": context_case_count,
            "intent_subintent_pair_count": len(dataset_pairs),
        }
        for count_field, expected_count in expected_benchmark_counts.items():
            if metadata.get(count_field) != expected_count:
                errors.append(
                    f"Dataset: metadata.{count_field} debe ser {expected_count}."
                )
        for profile_id in sorted(canonical_profile_ids):
            if cases_by_profile.get(profile_id) != 30:
                errors.append(
                    f"Dataset: '{profile_id}' tiene {cases_by_profile.get(profile_id, 0)} casos; se esperaban 30."
                )
            if not 6 <= contexts_by_profile.get(profile_id, 0) <= 9:
                errors.append(
                    f"Dataset: '{profile_id}' debe tener entre 6 y 9 casos con contexto."
                )

        uncovered_dataset_pairs = sorted(valid_pairs - dataset_pairs)
        if uncovered_dataset_pairs:
            errors.append(
                "Dataset sin cobertura de subintenciones: " + ", ".join(uncovered_dataset_pairs)
            )
        underrepresented_pairs = sorted(
            pair for pair, count in pair_counts.items() if count < 8
        )
        if underrepresented_pairs:
            errors.append(
                "Dataset: subintenciones con menos de ocho casos: "
                + ", ".join(underrepresented_pairs)
            )

    return errors


class ResourceJsonValidatorTests(unittest.TestCase):
    def test_resources_are_cross_referenced_and_unambiguous(self):
        self.assertEqual(validate(), [])


def main() -> int:
    errors = validate()
    if errors:
        print("Recursos inválidos:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Los JSON generales son válidos y sus referencias son coherentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
