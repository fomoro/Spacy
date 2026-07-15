"""Valida la coherencia cruzada de los recursos declarativos del motor."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "resources"
DATASET_JSON = RESOURCES / "corpus" / "datasets" / "customer_intent_benchmark.json"
RESOURCE_PATHS = {
    "intent_taxonomy.json": RESOURCES / "config" / "intent_taxonomy.json",
    "text_normalizer_service_config.json": RESOURCES / "config" / "infrastructure_nlp" / "text_normalizer_service_config.json",
    "matcher_service_config.json": RESOURCES / "config" / "infrastructure_nlp" / "matcher_service_config.json",
    "lemma_service_config.json": RESOURCES / "config" / "infrastructure_nlp" / "lemma_service_config.json",
    "entity_ruler_service_config.json": RESOURCES / "config" / "infrastructure_nlp" / "entity_ruler_service_config.json",
    "intent_resolver_config.json": RESOURCES / "config" / "application" / "intent_resolver_config.json",
    "clarification_policy.json": RESOURCES / "config" / "application" / "clarification_policy.json",
    "phrase_matcher_service_config.json": (
        RESOURCES / "config" / "infrastructure_nlp" / "phrase_matcher_service_config.json"
    ),
    "menu_offerings.json": RESOURCES / "data" / "menu" / "menu_offerings.json",
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
    if missing:
        return [f"Faltan recursos: {', '.join(missing)}"]

    taxonomy = load("intent_taxonomy.json")
    menu = load("phrase_matcher_service_config.json")
    offerings = load("menu_offerings.json")
    normalizer = load("text_normalizer_service_config.json")
    matcher = load("matcher_service_config.json")
    lemmas = load("lemma_service_config.json")
    ruler = load("entity_ruler_service_config.json")
    resolver = load("intent_resolver_config.json")
    clarification = load("clarification_policy.json")
    profiles = load("conversation_profiles.json")
    valid_pairs = taxonomy_pairs(taxonomy)
    covered_pairs: set[str] = set()

    if not isinstance(normalizer.get("options"), dict):
        errors.append("text_normalizer_service_config.json: falta 'options'.")

    pattern_ids: set[str] = set()
    for pattern in matcher.get("patterns", []):
        rule_id = str(pattern.get("id", ""))
        if not rule_id:
            errors.append("matcher_service_config.json: hay una regla sin id.")
        elif rule_id in pattern_ids:
            errors.append(f"Matcher: id duplicado '{rule_id}'.")
        pattern_ids.add(rule_id)
        pair = evidence_pair(pattern)
        covered_pairs.add(pair)
        if pair not in valid_pairs:
            errors.append(f"Matcher: '{rule_id}' referencia '{pair}' fuera de la taxonomía.")

    for signal in lemmas.get("signals", []):
        for evidence in signal.get("evidence", []):
            pair = evidence_pair(evidence)
            covered_pairs.add(pair)
            if pair not in valid_pairs:
                errors.append(f"Lemma '{signal.get('lemma')}' referencia '{pair}' fuera de la taxonomía.")

    resolver_evidence: list[dict[str, Any]] = []
    for mapping_name in ("phrase_evidence", "entity_ruler_evidence"):
        for items in resolver.get(mapping_name, {}).values():
            resolver_evidence.extend(items)
    resolver_evidence.extend(resolver.get("service_entity_map", {}).values())
    for evidence in resolver_evidence:
        pair = evidence_pair(evidence)
        covered_pairs.add(pair)
        if pair not in valid_pairs:
            errors.append(f"Resolver referencia '{pair}' fuera de la taxonomía.")
    for legacy_key in ("required_entities", "clarification_messages"):
        if legacy_key in resolver:
            errors.append(
                f"Resolver: '{legacy_key}' pertenece a clarification_policy.json."
            )

    modes = clarification.get("intervention_modes", {})
    slots = clarification.get("slots", {})
    policies = clarification.get("policies", {})
    questions = clarification.get("questions", {})
    for field, value in (
        ("intervention_modes", modes),
        ("slots", slots),
        ("policies", policies),
        ("questions", questions),
    ):
        if not isinstance(value, dict) or not value:
            errors.append(f"Aclaraciones: '{field}' debe ser un objeto no vacío.")

    allowed_placeholders = set(slots) | {"options"}
    for question_key, question in questions.items():
        if not isinstance(question, dict) or not str(question.get("template", "")).strip():
            errors.append(f"Aclaraciones: pregunta '{question_key}' sin template.")
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
                errors.append(f"Aclaraciones: formato inválido en '{question_key}': {exc}.")
                continue
            unknown = placeholders - allowed_placeholders
            if unknown:
                errors.append(
                    f"Aclaraciones: '{question_key}' usa slots desconocidos: "
                    + ", ".join(sorted(unknown))
                )

    for pair, policy in policies.items():
        if pair not in valid_pairs:
            errors.append(f"Aclaraciones: política '{pair}' fuera de la taxonomía.")
        if not isinstance(policy, dict):
            errors.append(f"Aclaraciones: política '{pair}' debe ser un objeto.")
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
                f"Aclaraciones {pair}: slots desconocidos: "
                + ", ".join(sorted(unknown_slots))
            )
        for mode_field in ("on_missing", "on_complete"):
            mode = policy.get(mode_field)
            if mode is not None and mode not in modes:
                errors.append(f"Aclaraciones {pair}: modo desconocido '{mode}'.")
        question_by_slot = policy.get("question_by_slot", {})
        expected_question_slots = set(required) | {
            "|".join(group) for group in required_any if group
        }
        missing_question_slots = expected_question_slots - set(question_by_slot)
        if missing_question_slots:
            errors.append(
                f"Aclaraciones {pair}: faltan preguntas para "
                + ", ".join(sorted(missing_question_slots))
            )
        referenced_questions = list(question_by_slot.values())
        if policy.get("complete_question"):
            referenced_questions.append(policy["complete_question"])
        for question_key in referenced_questions:
            if question_key not in questions:
                errors.append(
                    f"Aclaraciones {pair}: pregunta desconocida '{question_key}'."
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

    offering_metadata = offerings.get("metadata", {})
    if offering_metadata.get("currency") != "COP":
        errors.append("Ofertas: metadata.currency debe ser 'COP'.")
    if set(offering_metadata.get("allowed_types", [])) != {"fixed", "by_size"}:
        errors.append("Ofertas: metadata.allowed_types debe declarar fixed y by_size.")

    offering_ids: set[str] = set()
    offering_product_ids: set[str] = set()
    valid_price_types = {"fixed", "by_size"}
    forbidden_price_fields = {
        "source_value",
        "temporary",
        "requires_confirmation",
        "minimum",
        "maximum",
    }
    for product in offerings.get("products", []):
        product_id = str(product.get("product_id", ""))
        if not product_id:
            errors.append("Ofertas: existe un producto sin product_id.")
        elif product_id in offering_product_ids:
            errors.append(f"Ofertas: product_id duplicado '{product_id}'.")
        offering_product_ids.add(product_id)
        if product_id not in product_ids:
            errors.append(f"Ofertas: product_id desconocido '{product_id}'.")

        product_offerings = product.get("offerings", [])
        if not isinstance(product_offerings, list) or not product_offerings:
            errors.append(f"Ofertas {product_id}: debe contener al menos una oferta.")
            continue
        for offering in product_offerings:
            offering_id = str(offering.get("offering_id", ""))
            if not offering_id:
                errors.append("Ofertas: existe una oferta sin offering_id.")
            elif offering_id in offering_ids:
                errors.append(f"Ofertas: offering_id duplicado '{offering_id}'.")
            offering_ids.add(offering_id)

            price = offering.get("price", {})
            unexpected = forbidden_price_fields.intersection(price)
            if unexpected:
                errors.append(
                    f"Ofertas {offering_id}: campos de precio no permitidos "
                    + ", ".join(sorted(unexpected))
                    + "."
                )
            price_type = price.get("type")
            if price_type not in valid_price_types:
                errors.append(f"Ofertas {offering_id}: tipo de precio inválido '{price_type}'.")
            elif price_type == "fixed":
                amount = price.get("amount")
                if not isinstance(amount, int) or amount <= 0:
                    errors.append(
                        f"Ofertas {offering_id}: un precio fijo requiere amount entero positivo."
                    )
            elif price_type == "by_size":
                sizes = price.get("sizes", {})
                expected_sizes = {"pequeno", "mediano", "grande"}
                if set(sizes) != expected_sizes:
                    errors.append(
                        f"Ofertas {offering_id}: debe declarar pequeño, mediano y grande."
                    )
                elif not all(
                    isinstance(value, int) and value > 0 for value in sizes.values()
                ):
                    errors.append(
                        f"Ofertas {offering_id}: los precios por tamaño deben ser enteros positivos."
                    )
                elif not sizes["pequeno"] < sizes["mediano"] < sizes["grande"]:
                    errors.append(
                        f"Ofertas {offering_id}: los precios por tamaño deben ser crecientes."
                    )

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

    if not DATASET_JSON.is_file():
        errors.append("Dataset: falta customer_intent_benchmark.json.")
    else:
        dataset = json.loads(DATASET_JSON.read_text(encoding="utf-8"))
        dataset_cases = dataset.get("cases", []) if isinstance(dataset, dict) else []
        metadata = dataset.get("metadata", {}) if isinstance(dataset, dict) else {}
        if not isinstance(dataset, dict) or set(dataset) != {"metadata", "cases"}:
            errors.append("Dataset JSON: la raíz debe contener solo metadata y cases.")
        if not isinstance(dataset_cases, list):
            errors.append("Dataset JSON: 'cases' debe ser una lista.")
            dataset_cases = []
        expected_metadata_fields = {
            "schema_version", "purpose", "language", "domain",
            "profiles_reference", "taxonomy_reference",
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
        valid_modes = {"resolved", *modes.keys()}
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
                "expected_entities", "annotation",
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
                for boolean_key in ("pedido_activo", "menu_enviado_previamente"):
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
                "intent", "subintent", "intervention_mode", "missing_slots",
                "question_key",
            }
            if not isinstance(expected, dict) or set(expected) != expected_fields:
                errors.append(f"Dataset {case_id}: expected no coincide con el esquema mínimo.")
                expected = expected if isinstance(expected, dict) else {}
            pair = f"{expected.get('intent')}.{expected.get('subintent')}"
            dataset_pairs.add(pair)
            if pair not in valid_pairs:
                errors.append(f"Dataset {case_id}: '{pair}' no existe en la taxonomía.")
            mode = expected.get("intervention_mode")
            if mode not in valid_modes:
                errors.append(f"Dataset {case_id}: modo desconocido '{mode}'.")
            modes_by_profile.setdefault(profile_id, set()).add(str(mode))
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
            missing_slots = expected.get("missing_slots", [])
            if not isinstance(missing_slots, list):
                errors.append(f"Dataset {case_id}: missing_slots debe ser una lista.")
                missing_slots = []
            for raw_slot in missing_slots:
                for slot in str(raw_slot).split("|"):
                    if slot not in slots:
                        errors.append(f"Dataset {case_id}: slot desconocido '{slot}'.")
            question_key = expected.get("question_key")
            if question_key is not None and question_key not in valid_question_keys:
                errors.append(f"Dataset {case_id}: question_key desconocida '{question_key}'.")

            annotation = case.get("annotation", {})
            expected_annotation_fields = {
                "target_evidence", "disambiguating_evidence", "excluded_readings",
                "expected_action",
            }
            if not isinstance(annotation, dict) or set(annotation) != expected_annotation_fields:
                errors.append(f"Dataset {case_id}: annotation no coincide con el contrato.")
            else:
                for field in (
                    "target_evidence", "disambiguating_evidence", "expected_action",
                ):
                    if not isinstance(annotation.get(field), str) or not annotation[field].strip():
                        errors.append(f"Dataset {case_id}: annotation.{field} debe ser texto.")
                if annotation.get("target_evidence") not in raw_message:
                    errors.append(f"Dataset {case_id}: target_evidence no aparece en el mensaje.")
                if annotation.get("disambiguating_evidence") not in raw_message:
                    errors.append(
                        f"Dataset {case_id}: disambiguating_evidence no aparece en el mensaje."
                    )
                excluded = annotation.get("excluded_readings")
                if not isinstance(excluded, list) or not all(
                    isinstance(value, str) and value.strip() for value in excluded
                ):
                    errors.append(
                        f"Dataset {case_id}: annotation.excluded_readings debe ser una lista de textos."
                    )
                elif any(value not in valid_pairs for value in excluded):
                    errors.append(
                        f"Dataset {case_id}: excluded_readings contiene lecturas no canónicas."
                    )

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
        if sum(contexts_by_profile.values()) != 150:
            errors.append(
                f"Dataset: se esperaban 150 casos con contexto y hay "
                f"{sum(contexts_by_profile.values())}."
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
            if modes_by_profile.get(profile_id, set()) != valid_modes:
                errors.append(
                    f"Dataset: '{profile_id}' debe cubrir los cinco modos de intervención."
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


class ResourceContractTests(unittest.TestCase):
    def test_resources_are_cross_referenced_and_unambiguous(self):
        self.assertEqual(validate(), [])


def main() -> int:
    errors = validate()
    if errors:
        print("Recursos inválidos:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Recursos válidos: taxonomía, propietarios, dataset y referencias son coherentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
