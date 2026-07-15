from __future__ import annotations

import sys
"""Consola manual para MatcherService."""

from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizerService, PhraseMatcherService, MatcherService


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    normalizer_path = ROOT / "resources" / "config" / "infrastructure_nlp" / "text_normalizer_service_config.json"
    matcher_path = ROOT / "resources" / "config" / "infrastructure_nlp" / "matcher_service_config.json"
    business_entity_catalog_path = (
        ROOT
        / "resources"
        / "config"
        / "infrastructure_nlp"
        / "phrase_matcher_service_config.json"
    )

    try:
        normalizer = TextNormalizerService(normalizer_path)
        phrase_matcher = PhraseMatcherService(business_entity_catalog_path)
        matcher = MatcherService(matcher_path, phrase_matcher)
    except Exception as exc:
        print(f"❌ Error cargando configuración: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DEL MATCHER DE INTENCIONES (FASE 6)")
    print(" Escribe un mensaje para normalizar, extraer vocabulario y detectar intenciones.")
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
            # 1. Normalizar
            norm_result = normalizer.normalize(user_input)

            # 2. Analizar con Matcher (encadena PhraseMatcher por debajo)
            result = matcher.analyze(norm_result.normalized)

            print("-" * 60)
            print(f"📝 Original:      '{norm_result.original}'")
            print(f"✨ Normalizado:   '{norm_result.normalized}'")
            print("-" * 60)

            # Mostrar Evidencias de Intención
            print("🎯 Evidencias de Intención Detectadas:")
            if not result.evidence:
                print("  (Ninguna evidencia de intención detectada)")
            else:
                for idx, ev in enumerate(result.evidence, 1):
                    print(f"  {idx}. [{ev.intent.upper()}] Subintención: '{ev.subintent}' | Regla: {ev.rule_id} | Peso: {ev.weight:.2f}")

            print("-" * 60)
            # Mostrar Extracción Sintáctica y de Datos
            print("📊 Extracción de Datos y Sintaxis:")
            print(f"  • Cantidades:         {result.extraction.quantities}")
            print(f"  • Valores Monetarios: {result.extraction.monetary_values} pesos")
            print(f"  • ¿Tiene Negación?:   {'Sí' if result.extraction.has_negation else 'No'}")
            print(f"  • Platos/Vocabulario: {list(result.extraction.referenced_entities)}")

            print("=" * 60)

        except Exception as exc:
            print(f"❌ Error procesando el mensaje: {exc}")


if __name__ == "__main__":
    main()
