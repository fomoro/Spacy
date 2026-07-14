from __future__ import annotations

import sys
from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizer, PhraseMatcherService


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    normalizer_path = ROOT / "resources" / "nlp" / "normalizer_config.json"
    catalog_path = ROOT / "resources" / "menu" / "menu_catalog.json"
    
    try:
        normalizer = TextNormalizer(normalizer_path)
        matcher = PhraseMatcherService(catalog_path)
    except Exception as exc:
        print(f"❌ Error cargando configuración: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DEL PHRASE MATCHER (FASE 4)")
    print(" Escribe un mensaje para normalizar y extraer entidades.")
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
            
            # 2. Matcher
            match_result = matcher.match(norm_result.normalized)
            
            print("-" * 60)
            print(f"📝 Original:      '{norm_result.original}'")
            print(f"✨ Normalizado:   '{norm_result.normalized}'")
            
            if norm_result.monetary_values:
                print(f"💰 Valores Mon.:   {norm_result.monetary_values}")

            print("-" * 60)
            print("🔍 Entidades Detectadas:")
            if not match_result.entities:
                print("  (Ninguna entidad detectada)")
            else:
                for idx, ent in enumerate(match_result.entities, 1):
                    print(f"  {idx}. [{ent.entity_type}] ID: {ent.entity_id} | Canonical: '{ent.canonical}' | Texto: '{ent.text}'")

            if match_result.discarded_overlaps:
                print("-" * 60)
                print("⚠️  Entidades Descartadas (Solapamientos):")
                for idx, ent in enumerate(match_result.discarded_overlaps, 1):
                    print(f"  {idx}. [{ent.entity_type}] ID: {ent.entity_id} | Texto: '{ent.text}' (Prioridad: {ent.priority})")

            print("=" * 60)

        except Exception as exc:
            print(f"❌ Error procesando el mensaje: {exc}")


if __name__ == "__main__":
    main()
