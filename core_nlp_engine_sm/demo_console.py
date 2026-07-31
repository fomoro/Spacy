"""Demo interactivo del pipeline NLP completo.

Este archivo es el punto de composicion para desarrollo: conecta los servicios
reales del proyecto, recibe texto por consola y muestra la respuesta junto con
la decision tomada por el motor. No ejecuta operaciones transaccionales ni
persiste contexto entre turnos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.application import (
    DialogueOrchestrator,
    IntentResolver,
    LinguisticEvidenceMapper,
    LinguisticParser,
    ResolvedNlpResult,
    ResponseRenderer,
)
from src.infrastructure import (
    EntityRulerService,
    LemmaService,
    MatcherService,
    PhraseMatcherService,
    TextNormalizerService,
)


ROOT = Path(__file__).resolve().parent


def load_static_response_values(root: Path = ROOT) -> dict[str, Any]:
    """Carga datos no transaccionales que el demo puede responder con seguridad."""
    profile_path = (
        root
        / "resources"
        / "business_data"
        / "restaurant"
        / "restaurant_profile.json"
    )
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    restaurant = payload.get("restaurant")
    if not isinstance(restaurant, Mapping):
        raise ValueError("restaurant_profile.json no contiene 'restaurant'.")

    address = restaurant.get("address", {})
    if not isinstance(address, Mapping):
        address = {}
    address_parts = [
        str(address.get(field, "")).strip()
        for field in ("street", "neighborhood")
        if str(address.get(field, "")).strip()
    ]
    payment_methods = restaurant.get("payment_methods", [])
    if not isinstance(payment_methods, list):
        payment_methods = []

    return {
        "restaurant_name": str(restaurant.get("name", "")).strip(),
        "address": ", ".join(address_parts),
        "city": str(address.get("city", "")).strip(),
        "payment_methods": ", ".join(
            str(method).replace("_", " ") for method in payment_methods
        ),
    }


def build_pipeline(root: Path = ROOT) -> DialogueOrchestrator:
    """Construye el pipeline con los recursos versionados del proyecto."""
    infrastructure_resources = root / "src" / "infrastructure" / "resources"
    application_resources = root / "src" / "application" / "resources"

    parser = LinguisticParser(
        TextNormalizerService(
            infrastructure_resources / "text_normalizer_service_config.json"
        ),
        PhraseMatcherService(
            infrastructure_resources / "phrase_matcher_service_config.json"
        ),
        MatcherService(infrastructure_resources / "matcher_service_config.json"),
        LemmaService(infrastructure_resources / "lemma_service_config.json"),
        EntityRulerService(
            infrastructure_resources / "entity_ruler_service_config.json"
        ),
    )
    return DialogueOrchestrator(
        parser,
        LinguisticEvidenceMapper(
            application_resources / "linguistic_evidence_mapping.json"
        ),
        IntentResolver(root / "src" / "domain" / "resources"),
        ResponseRenderer(application_resources / "response_templates.json"),
    )


def parse_json_object(raw: str | None, option: str) -> dict[str, Any]:
    """Convierte una opcion JSON y exige que su raiz sea un objeto."""
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"{option} no contiene JSON valido: {error.msg}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{option} debe contener un objeto JSON.")
    return value


def parse_assignments(items: Sequence[str], option: str) -> dict[str, Any]:
    """Convierte pares clave=valor; interpreta escalares JSON cuando es posible."""
    parsed: dict[str, Any] = {}
    for item in items:
        key, separator, raw_value = item.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"{option} requiere el formato clave=valor: {item!r}")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        parsed[key.strip()] = value
    return parsed


def concise_output(result: ResolvedNlpResult) -> str:
    """Presenta la decision principal sin ocultar faltantes ni entidades."""
    resolution = result.resolution
    pair = ".".join(
        part for part in (resolution.intent, resolution.subintent) if part
    ) or "sin_intencion"
    entity_labels = [
        str(entity.get("canonical") or entity.get("text"))
        for entity in resolution.entities
        if entity.get("canonical") or entity.get("text")
    ]
    lines = [
        f"Bot: {result.response.text}",
        f"NLU: {pair} | confianza={resolution.confidence:.4f} "
        f"| modo={resolution.intervention_mode}",
        f"Normalizado: {result.evidence.normalized_text}",
    ]
    if entity_labels:
        lines.append("Entidades: " + ", ".join(entity_labels))
    if resolution.missing_slots:
        lines.append("Slots pendientes: " + ", ".join(resolution.missing_slots))
    if result.response.missing_values:
        lines.append(
            "Datos comerciales no suministrados: "
            + ", ".join(result.response.missing_values)
        )
    return "\n".join(lines)


def analyze_and_print(
    pipeline: DialogueOrchestrator,
    text: str,
    *,
    context: Mapping[str, Any],
    response_values: Mapping[str, Any],
    full_json: bool,
) -> None:
    result = pipeline.analyze(text, context, response_values)
    if full_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(concise_output(result))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demo por consola del motor NLP del restaurante."
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="Mensaje a analizar. Si se omite, inicia el modo interactivo.",
    )
    parser.add_argument(
        "--context-json",
        help="Contexto validado para el resolutor, como objeto JSON.",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="CLAVE=VALOR",
        help="Campo de contexto. Se puede repetir; true, false y numeros se tipan.",
    )
    parser.add_argument(
        "--values-json",
        help="Datos comerciales validados para la respuesta, como objeto JSON.",
    )
    parser.add_argument(
        "--value",
        action="append",
        default=[],
        metavar="CLAVE=VALOR",
        help="Dato comercial para renderizar. Se puede repetir.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Muestra evidencia, resolucion y respuesta completas en JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        context = parse_json_object(args.context_json, "--context-json")
        response_values = load_static_response_values()
        response_values.update(
            parse_json_object(args.values_json, "--values-json")
        )
        context.update(parse_assignments(args.context, "--context"))
        response_values.update(parse_assignments(args.value, "--value"))
    except ValueError as error:
        parser.error(str(error))

    pipeline = build_pipeline()
    one_shot_text = " ".join(args.text).strip()
    if one_shot_text:
        analyze_and_print(
            pipeline,
            one_shot_text,
            context=context,
            response_values=response_values,
            full_json=args.json,
        )
        return 0

    print("Motor NLP listo. Escribe un mensaje; usa 'salir' para terminar.")
    while True:
        try:
            text = input("Cliente> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text.casefold() in {"salir", "exit", "quit"}:
            return 0
        if not text:
            continue
        analyze_and_print(
            pipeline,
            text,
            context=context,
            response_values=response_values,
            full_json=args.json,
        )
        print()


if __name__ == "__main__":
    raise SystemExit(main())
