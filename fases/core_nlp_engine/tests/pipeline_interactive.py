from __future__ import annotations

import sys
import json
from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizer, PhraseMatcherService, MatcherService, LemmaService
from src.application import LinguisticParser


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    try:
        normalizer = TextNormalizer(ROOT / "resources" / "rules_config.json")
        phrase_matcher = PhraseMatcherService(ROOT / "resources" / "menu_catalog.json")
        matcher = MatcherService(ROOT / "resources" / "rules_config.json", phrase_matcher)
        lemmas = LemmaService(ROOT / "resources" / "rules_config.json")
        pipeline = LinguisticParser(normalizer, phrase_matcher, matcher, lemmas)
    except Exception as exc:
        print(f"❌ Error cargando configuración del pipeline: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DEL PIPELINE DE NLP COMPLETO")
    print(" Escribe un mensaje para ver el NlpEvidenceBundle consolidado.")
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
            print("📦 NlpEvidenceBundle (JSON):")
            print(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2))
            print("=" * 60)

        except Exception as exc:
            print(f"❌ Error al procesar en el pipeline: {exc}")


if __name__ == "__main__":
    main()
