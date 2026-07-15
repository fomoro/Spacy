"""Evaluación masiva de LemmaService sobre el dataset canónico."""

from pathlib import Path
import csv
import json
import sys

# Setup project root path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizerService
from src.application import LinguisticParser

CASES = ROOT / "resources" / "corpus" / "datasets" / "intent_benchmark" / "casos_intenciones_clientes.json"
OUTPUT = ROOT / "reports" / "lemma" / "evaluacion_lemas_dataset.csv"
SUMMARY = ROOT / "reports" / "lemma" / "resultado_lemas.json"


def main() -> None:
    normalizer = TextNormalizerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "text_normalizer_service_config.json")
    phrase = PhraseMatcherService(
        ROOT
        / "resources"
        / "config"
        / "infrastructure_nlp"
        / "phrase_matcher_service_config.json"
    )
    matcher = MatcherService(ROOT / "resources" / "config" / "infrastructure_nlp" / "matcher_service_config.json", phrase)
    lemmas = LemmaService(ROOT / "resources" / "config" / "infrastructure_nlp" / "lemma_service_config.json")
    ruler = EntityRulerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "entity_ruler_service_config.json")
    pipeline = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)

    if not CASES.exists():
        print(f"❌ No se encontró el archivo de casos en {CASES}")
        sys.exit(1)

    payload = json.loads(CASES.read_text(encoding="utf-8"))
    cases = payload["cases"] if isinstance(payload, dict) else payload

    rows = []
    with_lemma_evidence = 0
    exact_subintent_support = 0
    errors = 0
    source_counter = {"spacy": 0, "catalog_fallback": 0, "surface": 0}

    for case in cases:
        try:
            result = pipeline.analyze(case["message"])
            lemma_payload = result.lemmas
            evidence = lemma_payload["evidence"]
            if evidence:
                with_lemma_evidence += 1

            expected_subintent = case["expected"]["subintent"]
            supports_expected = any(
                item["subintent"] == expected_subintent for item in evidence
            )
            if supports_expected:
                exact_subintent_support += 1

            for token in lemma_payload["tokens"]:
                source_counter[token["source"]] = source_counter.get(token["source"], 0) + 1

            rows.append({
                "caso_id": case.get("id", ""),
                "perfil": case["profile_id"],
                "mensaje": case["message"],
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
                "perfil": case.get("profile_id", ""),
                "mensaje": case.get("message", ""),
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
