"""Evaluación de DialogueOrchestrator sobre el benchmark canónico."""

import csv
from collections import defaultdict
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
    DialogueOrchestrator,
    IntentResolver,
    LinguisticParser,
    ResponseRenderer,
)
from src.application import LinguisticEvidenceMapper

CASES = ROOT / "resources" / "corpus" / "benchmarks" / "customer_intent_benchmark.json"
OUTPUT = ROOT / "reports" / "resolver" / "evaluacion_resolutor_dataset.csv"
SUMMARY = ROOT / "reports" / "resolver" / "resultado_resolutor.json"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
phrase = PhraseMatcherService(
    ROOT / "src" / "infrastructure" / "resources" / "phrase_matcher_service_config.json"
)
matcher = MatcherService(ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json")
lemmas = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")
ruler = EntityRulerService(ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json")
evidence_mapper = LinguisticEvidenceMapper(ROOT / "src" / "application" / "resources" / "linguistic_evidence_mapping.json")
parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)
resolver = IntentResolver(ROOT / "src" / "domain" / "resources")
response_renderer = ResponseRenderer(
    ROOT / "src" / "application" / "resources" / "response_templates.json"
)
pipeline = DialogueOrchestrator(parser, evidence_mapper, resolver, response_renderer)

payload = json.loads(CASES.read_text(encoding="utf-8"))
cases = payload["cases"]
rows = []
intent_hits = 0
subintent_hits = 0
clarification_hits = 0
intervention_mode_hits = 0
missing_slots_hits = 0
question_key_hits = 0
excluded_reading_false_positives = 0
resolved = 0
ambiguous = 0
unknown = 0
errors = 0
clarification_tp = 0
clarification_fp = 0
clarification_fn = 0
clarification_tn = 0
intervention_modes: dict[str, int] = {}
slot_counts: dict[str, dict[str, int]] = defaultdict(
    lambda: {"true_positive": 0, "false_positive": 0, "false_negative": 0}
)

for case in cases:
    expected = case["expected"]
    try:
        result = pipeline.analyze(case["message"], case.get("context", {})).resolution
        intent_ok = result.intent == expected["intent"]
        subintent_ok = result.subintent == expected["subintent"]
        expected_clarification = expected["intervention_mode"] != "resolved"
        clarification_ok = result.requires_clarification == expected_clarification
        intervention_mode_ok = result.intervention_mode == expected["intervention_mode"]
        expected_slots = set(expected["missing_slots"])
        resolved_slots = set(result.missing_slots)
        missing_slots_ok = expected_slots == resolved_slots
        question_key_ok = result.question_key == expected["question_key"]
        resolved_pair = (
            f"{result.intent}.{result.subintent}"
            if result.intent is not None and result.subintent is not None
            else ""
        )
        excluded_reading_activated = resolved_pair in set(
            case.get("annotation", {}).get("excluded_readings", [])
        )
        intent_hits += int(intent_ok)
        subintent_hits += int(subintent_ok)
        clarification_hits += int(clarification_ok)
        intervention_mode_hits += int(intervention_mode_ok)
        missing_slots_hits += int(missing_slots_ok)
        question_key_hits += int(question_key_ok)
        excluded_reading_false_positives += int(excluded_reading_activated)
        for slot in expected_slots | resolved_slots:
            slot_counts[slot]["true_positive"] += int(
                slot in expected_slots and slot in resolved_slots
            )
            slot_counts[slot]["false_positive"] += int(
                slot not in expected_slots and slot in resolved_slots
            )
            slot_counts[slot]["false_negative"] += int(
                slot in expected_slots and slot not in resolved_slots
            )
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
            "slots_faltantes_esperados": json.dumps(sorted(expected_slots), ensure_ascii=False),
            "slots_faltantes_resueltos": json.dumps(sorted(resolved_slots), ensure_ascii=False),
            "slots_faltantes_correctos": missing_slots_ok,
            "clave_pregunta_esperada": expected["question_key"] or "",
            "clave_pregunta_resuelta": result.question_key or "",
            "clave_pregunta_correcta": question_key_ok,
            "lectura_excluida_activada": excluded_reading_activated,
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
            "slots_faltantes_esperados": json.dumps(expected.get("missing_slots", []), ensure_ascii=False),
            "slots_faltantes_resueltos": "[]", "slots_faltantes_correctos": False,
            "clave_pregunta_esperada": expected.get("question_key") or "",
            "clave_pregunta_resuelta": "", "clave_pregunta_correcta": False,
            "lectura_excluida_activada": False, "mensaje_aclaracion": "",
            "subintencion_correcta": False, "aclaracion_correcta": False,
            "reglas_aplicadas": "[]", "candidatos": "[]", "error": str(exc),
        })

with OUTPUT.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=rows[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
clarification_precision = clarification_tp / (clarification_tp + clarification_fp) if clarification_tp + clarification_fp else 0
clarification_recall = clarification_tp / (clarification_tp + clarification_fn) if clarification_tp + clarification_fn else 0
clarification_specificity = clarification_tn / (clarification_tn + clarification_fp) if clarification_tn + clarification_fp else 0
clarification_f1 = 2 * clarification_precision * clarification_recall / (clarification_precision + clarification_recall) if clarification_precision + clarification_recall else 0
slot_metrics = {}
for slot, counts in sorted(slot_counts.items()):
    tp = counts["true_positive"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    slot_metrics[slot] = {
        **counts,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
summary = {
    "casos_evaluados": total,
    "intencion_correcta": intent_hits,
    "subintencion_correcta": subintent_hits,
    "aclaracion_correcta": clarification_hits,
    "modo_intervencion_correcto": intervention_mode_hits,
    "slots_faltantes_exactos": missing_slots_hits,
    "clave_pregunta_correcta": question_key_hits,
    "precision_intencion_sobre_dataset": round(intent_hits / total, 4) if total else 0,
    "precision_subintencion_sobre_dataset": round(subintent_hits / total, 4) if total else 0,
    "precision_aclaracion_sobre_dataset": round(clarification_hits / total, 4) if total else 0,
    "precision_modo_intervencion_sobre_dataset": round(intervention_mode_hits / total, 4) if total else 0,
    "precision_slots_faltantes_sobre_dataset": round(missing_slots_hits / total, 4) if total else 0,
    "precision_clave_pregunta_sobre_dataset": round(question_key_hits / total, 4) if total else 0,
    "falsos_positivos_lecturas_excluidas": excluded_reading_false_positives,
    "metricas_por_slot": slot_metrics,
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
with SUMMARY.open("w", encoding="utf-8", newline="\n") as file:
    file.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False, indent=2))
