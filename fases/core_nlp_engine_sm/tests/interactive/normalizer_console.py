"""Consola manual para TextNormalizer."""

from __future__ import annotations

import sys
from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizer


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    config_path = ROOT / "resources" / "nlp" / "normalizer_config.json"
    try:
        normalizer = TextNormalizer(config_path)
    except Exception as exc:
        print(f"❌ Error cargando configuración desde {config_path}: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DEL NORMALIZADOR (FASE 4)")
    print(" Escribe un mensaje y presiona Enter para ver el resultado.")
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
            result = normalizer.normalize(user_input)
            
            print("-" * 60)
            print(f"📝 Original:   '{result.original}'")
            print(f"✨ Normalizado: '{result.normalized}'")
            
            # Mostrar valores monetarios si los hay
            if result.monetary_values:
                values_str = ", ".join(f"${val:,}" for val in result.monetary_values)
                print(f"💰 Monetario:   {values_str}")
                
            # Mostrar transformaciones si las hay
            if result.transformations:
                print("🔄 Transformaciones aplicadas:")
                for i, change in enumerate(result.transformations, 1):
                    rule_desc = change.rule
                    # Hacer la regla más legible si es de tipo phrase o alias
                    if rule_desc.startswith("phrase:"):
                        rule_desc = f"Frase '{rule_desc.split(':', 1)[1]}'"
                    elif rule_desc.startswith("alias:"):
                        rule_desc = f"Palabra '{rule_desc.split(':', 1)[1]}'"
                    
                    print(f"  {i}. [{rule_desc}]: '{change.before}' -> '{change.after}'")
            else:
                print("ℹ️  No se aplicaron transformaciones (el texto ya estaba normalizado).")
            print("-" * 60)
            
        except Exception as exc:
            print(f"❌ Ocurrió un error al normalizar: {exc}")


if __name__ == "__main__":
    main()
