import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizer, PhraseMatcherService, MatcherService

DATASET = ROOT / "tests" / "casos_contrato.json"
OUTPUT = ROOT / "reports" / "matcher" / "evaluacion_matcher.csv"
SUMMARY = ROOT / "reports" / "matcher" / "resultado_matcher.json"


def main() -> None:
    # Cargar configuraciones y servicios
    normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
    phrase_matcher = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")
    matcher = MatcherService(
        ROOT / "resources" / "nlp" / "matcher_patterns.json",
        phrase_matcher
    )

    # Cargar casos
    with DATASET.open(encoding="utf-8") as file:
        data = json.load(file)

    rows = []
    exact_matches = 0
    any_evidence_count = 0
    errors = 0

    for case in data["casos"]:
        try:
            # 1. Normalizar
            normalized = normalizer.normalize(case["mensaje"]).normalized

            # 2. Analizar intenciones y extraer entidades
            result = matcher.analyze(normalized)

            # 3. Validar si la intención/subintención esperada está en la evidencia
            detected_pairs = {(item.intent, item.subintent) for item in result.evidence}
            target_pair = (case["esperado"]["intencion"], case["esperado"]["subintencion"])

            has_exact = target_pair in detected_pairs
            exact_matches += int(has_exact)
            any_evidence_count += int(bool(result.evidence))

            rows.append({
                "caso_id": case["id"],
                "mensaje_original": case["mensaje"],
                "mensaje_normalizado": normalized,
                "intencion_esperada": ".".join(target_pair),
                "coincidencia_exacta": has_exact,
                "evidencia_detectada": json.dumps([item.to_dict() for item in result.evidence], ensure_ascii=False),
                "entidades_detectadas": json.dumps([item.to_dict() for item in result.phrase_entities], ensure_ascii=False),
                "extraccion_sintactica": json.dumps(result.extraction.to_dict(), ensure_ascii=False),
                "error": ""
            })
        except Exception as exc:
            errors += 1
            rows.append({
                "caso_id": case["id"],
                "mensaje_original": case["mensaje"],
                "mensaje_normalizado": "",
                "intencion_esperada": "",
                "coincidencia_exacta": False,
                "evidencia_detectada": "[]",
                "entidades_detectadas": "[]",
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
        "con_alguna_evidencia": any_evidence_count,
        "coincidencia_exacta_subintencion": exact_matches,
        "sin_coincidencia_exacta": len(rows) - exact_matches,
        "errores": errors,
        "cobertura_exacta_pct": round((exact_matches / len(rows)) * 100, 2) if rows else 0.0,
        "nota": "El Matcher de Intenciones sirve como extractor de evidencia lógica por reglas."
    }

    SUMMARY.write_text(
        json.dumps(summary_report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary_report, ensure_ascii=False))


if __name__ == "__main__":
    main()
