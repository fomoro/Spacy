"""Evaluación masiva de MatcherService sobre el benchmark canónico."""

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizerService, MatcherService

DATASET = ROOT / "resources" / "corpus" / "benchmarks" / "customer_intent_benchmark.json"
OUTPUT = ROOT / "reports" / "matcher" / "evaluacion_matcher.csv"
SUMMARY = ROOT / "reports" / "matcher" / "resultado_matcher.json"


def main() -> None:
    # Cargar configuraciones y servicios
    normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
    matcher = MatcherService(
        ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json"
    )

    # Cargar casos
    with DATASET.open(encoding="utf-8") as file:
        data = json.load(file)

    rows = []
    messages_with_signals = 0
    detected_signals = 0
    errors = 0

    for case in data["cases"]:
        try:
            # 1. Normalizar
            normalized = normalizer.normalize(case["message"]).normalized

            # 2. Detectar señales sintácticas sin usar entidades ni intenciones.
            result = matcher.analyze(normalized)
            messages_with_signals += int(bool(result.signals))
            detected_signals += len(result.signals)

            rows.append({
                "caso_id": case["id"],
                "perfil": case["profile_id"],
                "mensaje_original": case["message"],
                "mensaje_normalizado": normalized,
                "senales_sintacticas": json.dumps([item.to_dict() for item in result.signals], ensure_ascii=False),
                "extraccion_sintactica": json.dumps(result.extraction.to_dict(), ensure_ascii=False),
                "error": ""
            })
        except Exception as exc:
            errors += 1
            rows.append({
                "caso_id": case["id"],
                "perfil": case["profile_id"],
                "mensaje_original": case["message"],
                "mensaje_normalizado": "",
                "senales_sintacticas": "[]",
                "extraccion_sintactica": "{}",
                "error": str(exc)
            })

    # Guardar reporte CSV
    if rows:
        with OUTPUT.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    # Crear y guardar reporte JSON consolidado
    summary_report = {
        "total_casos": len(rows),
        "mensajes_con_senales_sintacticas": messages_with_signals,
        "total_senales_sintacticas": detected_signals,
        "errores": errors,
        "nota": "Cobertura técnica de señales sintácticas; la correspondencia con intenciones pertenece a la aplicación."
    }

    SUMMARY.write_text(
        json.dumps(summary_report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary_report, ensure_ascii=False))


if __name__ == "__main__":
    main()
