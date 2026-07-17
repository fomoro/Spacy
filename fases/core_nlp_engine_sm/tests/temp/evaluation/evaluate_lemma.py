"""Evaluación masiva de LemmaService sobre el benchmark canónico."""

from pathlib import Path
import csv
import json
import sys

# Setup project root path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.infrastructure import LemmaService, TextNormalizerService

CASES = ROOT / "resources" / "corpus" / "benchmarks" / "customer_intent_benchmark.json"
OUTPUT = ROOT / "reports" / "lemma" / "evaluacion_lemas_dataset.csv"
SUMMARY = ROOT / "reports" / "lemma" / "resultado_lemas.json"


def main() -> None:
    normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
    lemmas = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")

    if not CASES.exists():
        print(f"❌ No se encontró el archivo de casos en {CASES}")
        sys.exit(1)

    payload = json.loads(CASES.read_text(encoding="utf-8"))
    cases = payload["cases"] if isinstance(payload, dict) else payload

    rows = []
    with_lemma_signals = 0
    errors = 0
    source_counter = {"spacy": 0, "catalog_fallback": 0, "surface": 0}

    for case in cases:
        try:
            normalized = normalizer.normalize(case["message"]).normalized
            result = lemmas.analyze(normalized)
            signals = result.signals
            if signals:
                with_lemma_signals += 1

            for token in result.tokens:
                source_counter[token.source] = source_counter.get(token.source, 0) + 1

            rows.append({
                "caso_id": case.get("id", ""),
                "perfil": case["profile_id"],
                "mensaje": case["message"],
                "mensaje_normalizado": normalized,
                "senales_lemas": json.dumps([item.to_dict() for item in signals], ensure_ascii=False),
                "lemas": json.dumps(
                    [{"text": t.text, "lemma": t.lemma, "source": t.source}
                     for t in result.tokens],
                    ensure_ascii=False
                ),
                "error": "",
            })
        except Exception as exc:
            errors += 1
            rows.append({
                "caso_id": case.get("id", ""),
                "perfil": case.get("profile_id", ""),
                "mensaje": case.get("message", ""),
                "mensaje_normalizado": "",
                "senales_lemas": "[]",
                "lemas": "[]",
                "error": str(exc),
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "casos_evaluados": len(rows),
        "casos_con_senales_de_lemas": with_lemma_signals,
        "errores": errors,
        "modelo_con_lematizador": lemmas.model_has_lemmatizer,
        "fuentes_de_lema": source_counter,
        "nota": (
            "Las señales de lemas son neutrales. Su correspondencia con intenciones "
            "se evalúa en la capa de aplicación."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
