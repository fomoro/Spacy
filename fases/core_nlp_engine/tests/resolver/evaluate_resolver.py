
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import (
    TextNormalizer,
    PhraseMatcherService,
    MatcherService,
    LemmaService,
)
from src.application import (
    LinguisticParser,
    IntentEngine,
    IntentResolver,
)

CASES = ROOT / "tests" / "casos_contrato.json"
OUTPUT = ROOT / "reports" / "resolver" / "evaluacion_resolutor_contrato.csv"
SUMMARY = ROOT / "reports" / "resolver" / "resultado_resolutor.json"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

normalizer = TextNormalizer(ROOT / "resources" / "rules_config.json")
phrase = PhraseMatcherService(ROOT / "resources" / "menu_catalog.json")
matcher = MatcherService(ROOT / "resources" / "rules_config.json", phrase)
lemmas = LemmaService(ROOT / "resources" / "rules_config.json")
evidence = LinguisticParser(normalizer, phrase, matcher, lemmas)
resolver = IntentResolver(ROOT / "resources" / "rules_config.json")
pipeline = IntentEngine(evidence, resolver)

payload = json.loads(CASES.read_text(encoding="utf-8"))
cases = payload["casos"]
rows = []
intent_hits = 0
subintent_hits = 0
clarification_hits = 0
resolved = 0
ambiguous = 0
unknown = 0
errors = 0

for case in cases:
    expected = case["esperado"]
    try:
        result = pipeline.analyze(case["mensaje"], case.get("contexto_previo", {})).resolution
        intent_ok = result.intent == expected["intencion"]
        subintent_ok = result.subintent == expected["subintencion"]
        clarification_ok = result.requires_clarification == bool(expected.get("requiere_aclaracion", False))
        intent_hits += int(intent_ok)
        subintent_hits += int(subintent_ok)
        clarification_hits += int(clarification_ok)
        resolved += int(result.status == "resolved")
        ambiguous += int(result.status in {"ambiguous", "needs_clarification"})
        unknown += int(result.status == "unknown")
        rows.append({
            "caso_id": case["id"],
            "mensaje": case["mensaje"],
            "intencion_esperada": expected["intencion"],
            "subintencion_esperada": expected["subintencion"],
            "intencion_resuelta": result.intent or "",
            "subintencion_resuelta": result.subintent or "",
            "confianza": result.confidence,
            "estado": result.status,
            "requiere_aclaracion_esperado": expected.get("requiere_aclaracion", False),
            "requiere_aclaracion_resuelto": result.requires_clarification,
            "intencion_correcta": intent_ok,
            "subintencion_correcta": subintent_ok,
            "aclaracion_correcta": clarification_ok,
            "reglas_aplicadas": json.dumps(list(result.applied_rules), ensure_ascii=False),
            "candidatos": json.dumps([c.to_dict() for c in result.candidates], ensure_ascii=False),
            "error": "",
        })
    except Exception as exc:
        errors += 1
        rows.append({
            "caso_id": case.get("id", ""), "mensaje": case.get("mensaje", ""),
            "intencion_esperada": expected.get("intencion", ""),
            "subintencion_esperada": expected.get("subintencion", ""),
            "intencion_resuelta": "", "subintencion_resuelta": "", "confianza": 0,
            "estado": "error", "requiere_aclaracion_esperado": expected.get("requiere_aclaracion", False),
            "requiere_aclaracion_resuelto": True, "intencion_correcta": False,
            "subintencion_correcta": False, "aclaracion_correcta": False,
            "reglas_aplicadas": "[]", "candidatos": "[]", "error": str(exc),
        })

with OUTPUT.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
summary = {
    "casos_evaluados": total,
    "intencion_correcta": intent_hits,
    "subintencion_correcta": subintent_hits,
    "aclaracion_correcta": clarification_hits,
    "precision_intencion_sobre_contrato": round(intent_hits / total, 4) if total else 0,
    "precision_subintencion_sobre_contrato": round(subintent_hits / total, 4) if total else 0,
    "precision_aclaracion_sobre_contrato": round(clarification_hits / total, 4) if total else 0,
    "estados": {"resolved": resolved, "ambiguous_or_clarification": ambiguous, "unknown": unknown},
    "errores": errors,
    "nota": "Métrica sobre contrato compacto heredado de Fase 6; no reemplaza validación con conversaciones reales."
}
SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
