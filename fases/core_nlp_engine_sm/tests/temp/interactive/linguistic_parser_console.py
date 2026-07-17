"""Consola manual para LinguisticParser."""

from __future__ import annotations

import sys
import json
from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizerService
from src.temp import LinguisticParser
from src.temp import LinguisticEvidenceMapper


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    normalizer_path = ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json"
    matcher_path = ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json"
    lemma_path = ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json"
    ruler_path = ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json"
    business_entity_catalog_path = (
        ROOT
        / "src"
        / "infrastructure"
        / "resources"
        / "phrase_matcher_service_config.json"
    )

    try:
        normalizer = TextNormalizerService(normalizer_path)
        phrase_matcher = PhraseMatcherService(business_entity_catalog_path)
        matcher = MatcherService(matcher_path)
        lemmas = LemmaService(lemma_path)
        ruler = EntityRulerService(ruler_path)
        evidence_mapper = LinguisticEvidenceMapper(
            ROOT / "src" / "temp" / "resources" / "linguistic_evidence_mapping.json"
        )
        pipeline = LinguisticParser(
            normalizer, phrase_matcher, matcher, lemmas, ruler, evidence_mapper
        )
    except Exception as exc:
        print(f"❌ Error cargando configuración del pipeline: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DEL PIPELINE DE NLP COMPLETO")
    print(" Escribe un mensaje para ver el LinguisticEvidenceBundle consolidado.")
    print(" Escribe 'salir', 'exit' o 'quit' para terminar.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nMensaje > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 ¡Hasta luego!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit"):
            print("👋 ¡Hasta luego!")
            break

        try:
            bundle = pipeline.analyze(user_input)

            print("-" * 60)
            print(f"📝 Original:      '{bundle.original_text}'")
            print(f"✨ Normalizado:   '{bundle.normalized_text}'")
            print("-" * 60)

            # Imprimir el JSON del bundle
            print("📦 LinguisticEvidenceBundle (JSON):")
            print(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2))
            print("=" * 60)

        except Exception as exc:
            print(f"❌ Error al procesar en el pipeline: {exc}")


if __name__ == "__main__":
    main()
