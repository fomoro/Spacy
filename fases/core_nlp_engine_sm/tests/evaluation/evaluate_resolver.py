"""Evaluación de IntentEngine sobre el dataset canónico."""

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import (
    EntityRulerService,
    TextNormalizerService,
    PhraseMatcherService,
    MatcherService,
    LemmaService,
)
from src.application import (
    IntentEngine,
    IntentResolver,
    LinguisticParser,
)

CASES = ROOT / "resources" / "corpus" / "datasets" / "customer_intent_benchmark.json"
OUTPUT = ROOT / "reports" / "resolver" / "evaluacion_resolutor_dataset.csv"
SUMMARY = ROOT / "reports" / "resolver" / "resultado_resolutor.json"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

normalizer = TextNormalizerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "text_normalizer_service_config.json")
phrase = PhraseMatcherService(
    ROOT / "resources" / "config" / "infrastructure_nlp" / "phrase_matcher_service_config.json"
)
matcher = MatcherService(ROOT / "resources" / "config" / "infrastructure_nlp" / "matcher_service_config.json", phrase)
lemmas = LemmaService(ROOT / "resources" / "config" / "infrastructure_nlp" / "lemma_service_config.json")
ruler = EntityRulerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "entity_ruler_service_config.json")
parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)
resolver = IntentResolver(ROOT / "resources" / "config" / "application" / "intent_resolver_config.json")
pipeline = IntentEngine(parser, resolver)

payload = json.loads(CASES.read_text(encoding="utf-8"))
cases = payload["cases"]
rows = []
intent_hits = 0
subintent_hits = 0
clarification_hits = 0
intervention_mode_hits = 0
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
    expected = case["expected"]
    try:
        result = pipeline.analyze(case["message"], case.get("context", {})).resolution
        intent_ok = result.intent == expected["intent"]
        subintent_ok = result.subintent == expected["subintent"]
        expected_clarification = expected["intervention_mode"] != "resolved"
        clarification_ok = result.requires_clarification == expected_clarification
        intervention_mode_ok = result.intervention_mode == expected["intervention_mode"]
        intent_hits += int(intent_ok)
        subintent_hits += int(subintent_ok)
        clarification_hits += int(clarification_ok)
        intervention_mode_hits += int(intervention_mode_ok)
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
            "perfil": case["profile_id"],
            "mensaje": case["message"],
            "intencion_esperada": expected["intent"],
            "subintencion_esperada": expected["subintent"],
            "intencion_resuelta": result.intent or "",
            "subintencion_resuelta": result.subintent or "",
            "confianza": result.confidence,
            "estado": result.status,
            "requiere_aclaracion_esperado": expected_clarification,
            "requiere_aclaracion_resuelto": result.requires_clarification,
            "modo_intervencion_esperado": expected["intervention_mode"],
            "modo_intervencion_resuelto": result.intervention_mode,
            "razon_aclaracion": result.clarification_reason or "",
            "slots_faltantes": json.dumps(list(result.missing_slots), ensure_ascii=False),
            "clave_pregunta": result.question_key or "",
            "mensaje_aclaracion": result.clarification_message or "",
            "intencion_correcta": intent_ok,
            "subintencion_correcta": subintent_ok,
            "aclaracion_correcta": clarification_ok,
            "modo_intervencion_correcto": intervention_mode_ok,
            "reglas_aplicadas": json.dumps(list(result.applied_rules), ensure_ascii=False),
            "candidatos": json.dumps([c.to_dict() for c in result.candidates], ensure_ascii=False),
            "error": "",
        })
    except Exception as exc:
        errors += 1
        rows.append({
            "caso_id": case.get("id", ""), "perfil": case.get("profile_id", ""),
            "mensaje": case.get("message", ""),
            "intencion_esperada": expected.get("intent", ""),
            "subintencion_esperada": expected.get("subintent", ""),
            "intencion_resuelta": "", "subintencion_resuelta": "", "confianza": 0,
            "estado": "error",
            "requiere_aclaracion_esperado": expected.get("intervention_mode") != "resolved",
            "requiere_aclaracion_resuelto": True, "intencion_correcta": False,
            "modo_intervencion_esperado": expected.get("intervention_mode", ""),
            "modo_intervencion_resuelto": "error", "modo_intervencion_correcto": False,
            "razon_aclaracion": "error",
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
    "modo_intervencion_correcto": intervention_mode_hits,
    "precision_intencion_sobre_dataset": round(intent_hits / total, 4) if total else 0,
    "precision_subintencion_sobre_dataset": round(subintent_hits / total, 4) if total else 0,
    "precision_aclaracion_sobre_dataset": round(clarification_hits / total, 4) if total else 0,
    "precision_modo_intervencion_sobre_dataset": round(intervention_mode_hits / total, 4) if total else 0,
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
    "nota": "Métrica sobre 600 casos sintéticos; no reemplaza validación con conversaciones reales."
}
SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
