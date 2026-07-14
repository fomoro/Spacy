from __future__ import annotations

import json
from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
RESOURCE_PATHS = {
    "intent_taxonomy.json": RESOURCES / "nlp" / "intent_taxonomy.json",
    "normalizer_config.json": RESOURCES / "nlp" / "normalizer_config.json",
    "matcher_patterns.json": RESOURCES / "nlp" / "matcher_patterns.json",
    "lemma_signals.json": RESOURCES / "nlp" / "lemma_signals.json",
    "entity_ruler_patterns.json": RESOURCES / "nlp" / "entity_ruler_patterns.json",
    "resolver_config.json": RESOURCES / "nlp" / "resolver_config.json",
    "clarification_policy.json": RESOURCES / "dialogue" / "clarification_policy.json",
    "menu_catalog.json": RESOURCES / "menu" / "menu_catalog.json",
    "menu_offerings.json": RESOURCES / "menu" / "menu_offerings.json",
    "conversation_profiles.json": RESOURCES / "profiles" / "conversation_profiles.json",
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
    menu = load("menu_catalog.json")
    offerings = load("menu_offerings.json")
    normalizer = load("normalizer_config.json")
    matcher = load("matcher_patterns.json")
    lemmas = load("lemma_signals.json")
    ruler = load("entity_ruler_patterns.json")
    resolver = load("resolver_config.json")
    clarification = load("clarification_policy.json")
    profiles = load("conversation_profiles.json")
    valid_pairs = taxonomy_pairs(taxonomy)
    covered_pairs: set[str] = set()

    if not isinstance(normalizer.get("options"), dict):
        errors.append("normalizer_config.json: falta 'options'.")

    pattern_ids: set[str] = set()
    for pattern in matcher.get("patterns", []):
        rule_id = str(pattern.get("id", ""))
        if not rule_id:
            errors.append("matcher_patterns.json: hay una regla sin id.")
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
                errors.append(f"Menú {entity_type}: id duplicado '{entity_id}'.")
            ids.add(entity_id)
            if entity_type in {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}:
                product_ids.add(entity_id)
            for raw_phrase in item.get("phrases", []):
                phrase = " ".join(str(raw_phrase).casefold().split())
                if not phrase:
                    errors.append(f"Menú {entity_type}/{entity_id}: frase vacía.")
                    continue
                previous = phrase_owner.get(phrase)
                if previous and previous != entity_id:
                    errors.append(
                        f"Menú {entity_type}: frase '{phrase}' pertenece a '{previous}' y '{entity_id}'."
                    )
                phrase_owner[phrase] = entity_id
                menu_phrases.add(phrase)

    offering_ids: set[str] = set()
    valid_price_types = {"fixed", "range", "by_size", "unknown"}
    for offering in offerings.get("offerings", []):
        offering_id = str(offering.get("offering_id", ""))
        product_id = str(offering.get("product_id", ""))
        if not offering_id:
            errors.append("Ofertas: existe una oferta sin offering_id.")
        elif offering_id in offering_ids:
            errors.append(f"Ofertas: offering_id duplicado '{offering_id}'.")
        offering_ids.add(offering_id)
        if product_id not in product_ids:
            errors.append(f"Ofertas: product_id desconocido '{product_id}'.")
        price = offering.get("price", {})
        price_type = price.get("type")
        if price.get("temporary") is True and price.get("requires_confirmation") is not True:
            errors.append(f"Ofertas {offering_id}: un precio temporal debe requerir confirmación.")
        if price_type not in valid_price_types:
            errors.append(f"Ofertas {offering_id}: tipo de precio inválido '{price_type}'.")
        elif price_type == "fixed" and not isinstance(price.get("amount"), int):
            errors.append(f"Ofertas {offering_id}: un precio fijo requiere amount entero.")
        elif price_type == "range":
            minimum, maximum = price.get("minimum"), price.get("maximum")
            if not isinstance(minimum, int) or not isinstance(maximum, int) or minimum > maximum:
                errors.append(f"Ofertas {offering_id}: rango de precio inválido.")
        elif price_type == "by_size":
            sizes = price.get("sizes", {})
            expected_sizes = {"pequeno", "mediano", "grande"}
            if set(sizes) != expected_sizes:
                errors.append(f"Ofertas {offering_id}: debe declarar pequeño, mediano y grande.")
            elif not all(isinstance(value, int) and value > 0 for value in sizes.values()):
                errors.append(f"Ofertas {offering_id}: los precios por tamaño deben ser enteros positivos.")
            elif not sizes["pequeno"] < sizes["mediano"] < sizes["grande"]:
                errors.append(f"Ofertas {offering_id}: los precios por tamaño deben ser crecientes.")
            if price.get("temporary") is not True or price.get("requires_confirmation") is not True:
                errors.append(f"Ofertas {offering_id}: los valores temporales deben requerir confirmación.")
        elif price_type == "unknown" and price.get("requires_confirmation") is not True:
            errors.append(f"Ofertas {offering_id}: precio desconocido debe requerir confirmación.")

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
    if declared_count != 15 or len(profile_items) != 15:
        errors.append(
            f"Perfiles: se esperaban 15 perfiles; hay {len(profile_items)} "
            f"y profile_count declara {declared_count!r}."
        )
    if profiles.get("contains_cases") is not False:
        errors.append("Perfiles: 'contains_cases' debe ser false.")

    runtime_policy = profiles.get("runtime_policy", {})
    for policy_key in (
        "use_in_runtime_resolution",
        "infer_profile_from_message",
        "modify_business_rules_by_profile",
    ):
        if runtime_policy.get(policy_key) is not False:
            errors.append(f"Perfiles: runtime_policy.{policy_key} debe ser false.")

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

    contract = json.loads((ROOT / "tests" / "casos_contrato.json").read_text(encoding="utf-8"))
    for case in contract.get("casos", []):
        expected = case.get("esperado", {})
        pair = f"{expected.get('intencion')}.{expected.get('subintencion')}"
        if pair not in valid_pairs:
            errors.append(f"Contrato {case.get('id')}: '{pair}' no existe en la taxonomía.")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Recursos inválidos:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Recursos válidos: taxonomía, propietarios y referencias son coherentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
