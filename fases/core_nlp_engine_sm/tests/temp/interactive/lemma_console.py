"""Consola manual para LemmaService."""

from __future__ import annotations

import sys
from pathlib import Path

# Configurar path del proyecto
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizerService, LemmaService


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)


def main() -> None:
    normalizer_path = ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json"
    lemma_path = ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json"

    try:
        normalizer = TextNormalizerService(normalizer_path)
        lemmas = LemmaService(lemma_path)
    except Exception as exc:
        print(f"❌ Error cargando configuración: {exc}")
        sys.exit(1)

    print_header("PROBADOR INTERACTIVO DE LEMAS (FASE 7)")
    print(" Escribe un mensaje para normalizar y observar lemas y señales.")
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

            # 2. Analizar lemas
            result = lemmas.analyze(norm_result.normalized)

            print("-" * 60)
            print(f"📝 Original:      '{norm_result.original}'")
            print(f"✨ Normalizado:   '{norm_result.normalized}'")
            print(f"⚙️ Modelo spaCy:  {'Con lematizador' if result.model_has_lemmatizer else 'Sin lematizador (Fallback)'}")
            print("-" * 60)

            # Mostrar Tokens y sus Lemas
            print("🔤 Lemas de cada Token:")
            for t in result.tokens:
                print(f"  • Token: '{t.text}' | Lema: '{t.lemma}' | POS: {t.pos} | Origen: {t.source}")

            print("-" * 60)
            # Mostrar señales morfológicas neutrales.
            print("🎯 Señales de lemas:")
            if not result.signals:
                print("  (Ninguna señal de lema detectada)")
            else:
                for idx, signal in enumerate(result.signals, 1):
                    print(
                        f"  {idx}. Lema: '{signal.lemma}' | "
                        f"Texto: '{signal.matched_text}' | Origen: {signal.source}"
                    )

            print("=" * 60)

        except Exception as exc:
            print(f"❌ Error al procesar: {exc}")


if __name__ == "__main__":
    main()
