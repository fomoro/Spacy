from pathlib import Path
import csv
import json
import sys

# Setup project root path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizer
from src.application import LinguisticParser

CASES = ROOT / "tests" / "casos_contrato.json"
OUTPUT = ROOT / "reports" / "lemma" / "evaluacion_lemas_contrato.csv"
SUMMARY = ROOT / "reports" / "lemma" / "resultado_lemas.json"


def main() -> None:
    normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
    phrase = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")
    matcher = MatcherService(ROOT / "resources" / "nlp" / "matcher_patterns.json", phrase)
    lemmas = LemmaService(ROOT / "resources" / "nlp" / "lemma_signals.json")
    ruler = EntityRulerService(ROOT / "resources" / "nlp" / "entity_ruler_patterns.json")
    pipeline = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)

    if not CASES.exists():
        print(f"❌ No se encontró el archivo de casos en {CASES}")
        sys.exit(1)

    payload = json.loads(CASES.read_text(encoding="utf-8"))
    cases = payload["casos"] if isinstance(payload, dict) else payload

    rows = []
    with_lemma_evidence = 0
    exact_subintent_support = 0
    errors = 0
    source_counter = {"spacy": 0, "catalog_fallback": 0, "surface": 0}

    for case in cases:
        try:
            result = pipeline.analyze(case["mensaje"])
            lemma_payload = result.lemmas
            evidence = lemma_payload["evidence"]
            if evidence:
                with_lemma_evidence += 1

            expected_subintent = case.get("subintencion") or case.get("esperado", {}).get("subintencion")
            supports_expected = any(
                item["subintent"] == expected_subintent for item in evidence
            )
            if supports_expected:
                exact_subintent_support += 1

            for token in lemma_payload["tokens"]:
                source_counter[token["source"]] = source_counter.get(token["source"], 0) + 1

            rows.append({
                "caso_id": case.get("id", ""),
                "mensaje": case["mensaje"],
                "subintencion_esperada": expected_subintent,
                "mensaje_normalizado": result.normalized_text,
                "evidencias_matcher": json.dumps(result.matcher["evidence"], ensure_ascii=False),
                "evidencias_lemas": json.dumps(evidence, ensure_ascii=False),
                "lemas": json.dumps(
                    [{"text": t["text"], "lemma": t["lemma"], "source": t["source"]}
                     for t in lemma_payload["tokens"]],
                    ensure_ascii=False
                ),
                "lemas_apoyan_subintencion": supports_expected,
                "error": "",
            })
        except Exception as exc:
            errors += 1
            rows.append({
                "caso_id": case.get("id", ""),
                "mensaje": case.get("mensaje", ""),
                "subintencion_esperada": "",
                "mensaje_normalizado": "",
                "evidencias_matcher": "[]",
                "evidencias_lemas": "[]",
                "lemas": "[]",
                "lemas_apoyan_subintencion": False,
                "error": str(exc),
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "casos_evaluados": len(rows),
        "casos_con_evidencia_de_lemas": with_lemma_evidence,
        "casos_donde_lemas_apoyan_subintencion_esperada": exact_subintent_support,
        "errores": errors,
        "modelo_con_lematizador": lemmas.model_has_lemmatizer,
        "fuentes_de_lema": source_counter,
        "nota": (
            "La evidencia por lemas es secundaria. No se interpreta su cobertura "
            "aislada como precisión final del chatbot."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
