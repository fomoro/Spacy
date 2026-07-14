
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import (
    EntityRulerService,
    TextNormalizer,
    PhraseMatcherService,
    MatcherService,
    LemmaService,
)
from src.application import (
    IntentEngine,
    IntentResolver,
    LinguisticParser,
)

CASES = ROOT / "tests" / "casos_contrato.json"
OUTPUT = ROOT / "reports" / "resolver" / "evaluacion_resolutor_contrato.csv"
SUMMARY = ROOT / "reports" / "resolver" / "resultado_resolutor.json"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
phrase = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")
matcher = MatcherService(ROOT / "resources" / "nlp" / "matcher_patterns.json", phrase)
lemmas = LemmaService(ROOT / "resources" / "nlp" / "lemma_signals.json")
ruler = EntityRulerService(ROOT / "resources" / "nlp" / "entity_ruler_patterns.json")
parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)
resolver = IntentResolver(ROOT / "resources" / "nlp" / "resolver_config.json")
pipeline = IntentEngine(parser, resolver)

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
clarification_tp = 0
clarification_fp = 0
clarification_fn = 0
clarification_tn = 0
intervention_modes: dict[str, int] = {}

for case in cases:
    expected = case["esperado"]
    try:
        result = pipeline.analyze(case["mensaje"], case.get("contexto_previo", {})).resolution
        intent_ok = result.intent == expected["intencion"]
        subintent_ok = result.subintent == expected["subintencion"]
        expected_clarification = bool(expected.get("requiere_aclaracion", False))
        clarification_ok = result.requires_clarification == expected_clarification
        intent_hits += int(intent_ok)
        subintent_hits += int(subintent_ok)
        clarification_hits += int(clarification_ok)
        resolved += int(result.status == "resolved")
        ambiguous += int(result.requires_clarification and result.status != "unknown")
        unknown += int(result.status == "unknown")
        clarification_tp += int(expected_clarification and result.requires_clarification)
        clarification_fp += int(not expected_clarification and result.requires_clarification)
        clarification_fn += int(expected_clarification and not result.requires_clarification)
        clarification_tn += int(not expected_clarification and not result.requires_clarification)
        intervention_modes[result.intervention_mode] = intervention_modes.get(result.intervention_mode, 0) + 1
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
            "modo_intervencion": result.intervention_mode,
            "razon_aclaracion": result.clarification_reason or "",
            "slots_faltantes": json.dumps(list(result.missing_slots), ensure_ascii=False),
            "clave_pregunta": result.question_key or "",
            "mensaje_aclaracion": result.clarification_message or "",
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
            "modo_intervencion": "error", "razon_aclaracion": "error",
            "slots_faltantes": "[]", "clave_pregunta": "", "mensaje_aclaracion": "",
            "subintencion_correcta": False, "aclaracion_correcta": False,
            "reglas_aplicadas": "[]", "candidatos": "[]", "error": str(exc),
        })

with OUTPUT.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
clarification_precision = clarification_tp / (clarification_tp + clarification_fp) if clarification_tp + clarification_fp else 0
clarification_recall = clarification_tp / (clarification_tp + clarification_fn) if clarification_tp + clarification_fn else 0
clarification_specificity = clarification_tn / (clarification_tn + clarification_fp) if clarification_tn + clarification_fp else 0
clarification_f1 = 2 * clarification_precision * clarification_recall / (clarification_precision + clarification_recall) if clarification_precision + clarification_recall else 0
summary = {
    "casos_evaluados": total,
    "intencion_correcta": intent_hits,
    "subintencion_correcta": subintent_hits,
    "aclaracion_correcta": clarification_hits,
    "precision_intencion_sobre_contrato": round(intent_hits / total, 4) if total else 0,
    "precision_subintencion_sobre_contrato": round(subintent_hits / total, 4) if total else 0,
    "precision_aclaracion_sobre_contrato": round(clarification_hits / total, 4) if total else 0,
    "metricas_aclaracion": {
        "precision": round(clarification_precision, 4),
        "recall": round(clarification_recall, 4),
        "specificity": round(clarification_specificity, 4),
        "f1": round(clarification_f1, 4),
        "true_positive": clarification_tp,
        "false_positive": clarification_fp,
        "false_negative": clarification_fn,
        "true_negative": clarification_tn,
    },
    "estados": {"resolved": resolved, "ambiguous_or_clarification": ambiguous, "unknown": unknown},
    "modos_intervencion": dict(sorted(intervention_modes.items())),
    "errores": errors,
    "nota": "Métrica sobre contrato compacto heredado de Fase 6; no reemplaza validación con conversaciones reales."
}
SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
