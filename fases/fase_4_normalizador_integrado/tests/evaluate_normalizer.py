from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure.json_loader import load_json, load_normalizer_config
from src.nlp.normalizer import TextNormalizer


def main() -> None:
    normalizer = TextNormalizer(load_normalizer_config(ROOT / "resources" / "normalizer"))
    dataset = load_json(ROOT / "data" / "dataset_clientes.json")
    rows = []
    changed = 0
    errors = 0
    for case in dataset["casos"]:
        try:
            result = normalizer.normalize(case["mensaje"])
            changed += int(result.normalized != case["mensaje"])
            rows.append([
                case["id"], case["perfil_cliente_id"], case["mensaje"],
                result.normalized, len(result.transformations),
                json.dumps(result.monetary_values, ensure_ascii=False)
            ])
        except Exception as exc:
            errors += 1
            rows.append([case["id"], case["perfil_cliente_id"], case["mensaje"], "", -1, str(exc)])
    output = ROOT / "reports" / "evaluacion_normalizador.csv"
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["caso_id","perfil","original","normalizado","transformaciones","valores_monetarios"])
        writer.writerows(rows)
    report = {"total":len(rows),"modificados":changed,"sin_cambios":len(rows)-changed,"errores":errors}
    (ROOT / "reports" / "resultado_evaluacion.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
