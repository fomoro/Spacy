from pathlib import Path
import sys
import csv
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.infrastructure import TextNormalizer, PhraseMatcherService


DATASET = ROOT / "data" / "dataset_clientes.json"
OUTPUT = ROOT / "reports" / "phrase_matcher" / "evaluacion_phrase_matcher.csv"
SUMMARY = ROOT / "reports" / "phrase_matcher" / "resultado_phrase_matcher.json"

normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
matcher = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")

with DATASET.open(encoding="utf-8") as file:
    dataset = json.load(file)

rows = []
detected_total = 0
messages_with_entities = 0
errors = 0

for case in dataset["casos"]:
    try:
        normalized = normalizer.normalize(case["mensaje"]).normalized
        result = matcher.match(normalized)
        entities = [entity.to_dict() for entity in result.entities]
        detected_total += len(entities)
        if entities:
            messages_with_entities += 1
        rows.append({
            "caso_id": case["id"],
            "perfil": case["perfil_cliente_id"],
            "mensaje_original": case["mensaje"],
            "mensaje_normalizado": normalized,
            "intencion_esperada": case["intencion_esperada"],
            "entidades_fase1": json.dumps(case["entidades_esperadas"], ensure_ascii=False),
            "entidades_phrase_matcher": json.dumps(entities, ensure_ascii=False),
            "cantidad_entities": len(entities),
            "cantidad_descartadas_solapamiento": len(result.discarded_overlaps),
            "error": "",
        })
    except Exception as exc:
        errors += 1
        rows.append({
            "caso_id": case["id"],
            "perfil": case["perfil_cliente_id"],
            "mensaje_original": case["mensaje"],
            "mensaje_normalizado": "",
            "intencion_esperada": case["intencion_esperada"],
            "entidades_fase1": json.dumps(case["entidades_esperadas"], ensure_ascii=False),
            "entidades_phrase_matcher": "[]",
            "cantidad_entities": 0,
            "cantidad_descartadas_solapamiento": 0,
            "error": str(exc),
        })

with OUTPUT.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "caso_id",
            "perfil",
            "mensaje_original",
            "mensaje_normalizado",
            "intencion_esperada",
            "entidades_fase1",
            "entidades_phrase_matcher",
            "cantidad_entities",
            "cantidad_descartadas_solapamiento",
            "error",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

summary = {
    "total_casos": len(dataset["casos"]),
    "mensajes_con_entidades": messages_with_entities,
    "total_entidades_detectadas": detected_total,
    "errores": errors,
}

with SUMMARY.open("w", encoding="utf-8") as file:
    json.dump(summary, file, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False))
