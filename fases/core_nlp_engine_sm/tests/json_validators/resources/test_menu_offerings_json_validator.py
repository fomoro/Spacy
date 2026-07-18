"""Valida la estructura vigente de menu_offerings.json de forma independiente."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MENU_PATH = ROOT / "resources" / "business_data" / "menu" / "menu_offerings.json"


def require_exact_keys(
    value: Any,
    expected: set[str],
    location: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{location} debe ser un objeto.")
        return False
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append("faltan " + ", ".join(missing))
        if unexpected:
            details.append("sobran " + ", ".join(unexpected))
        errors.append(f"{location} tiene una estructura inválida: {'; '.join(details)}.")
        return False
    return True


def is_positive_integer(value: Any) -> bool:
    return type(value) is int and value > 0


def validate() -> list[str]:
    errors: list[str] = []
    if not MENU_PATH.is_file():
        return [f"No existe el menú: {MENU_PATH}"]

    try:
        menu = json.loads(MENU_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"No se pudo leer menu_offerings.json: {exc}"]

    if not require_exact_keys(
        menu,
        {"metadata", "recommendations", "products"},
        "Menú",
        errors,
    ):
        return errors

    metadata = menu["metadata"]
    if require_exact_keys(
        metadata,
        {"schema_version", "purpose", "currency", "allowed_types"},
        "Menú.metadata",
        errors,
    ):
        if metadata["schema_version"] != "3.0.0":
            errors.append("Menú.metadata.schema_version debe ser '3.0.0'.")
        if not isinstance(metadata["purpose"], str) or not metadata["purpose"].strip():
            errors.append("Menú.metadata.purpose debe ser texto no vacío.")
        if metadata["currency"] != "COP":
            errors.append("Menú.metadata.currency debe ser 'COP'.")
        allowed_types = metadata["allowed_types"]
        if (
            not isinstance(allowed_types, list)
            or len(allowed_types) != 2
            or set(allowed_types) != {"fixed", "by_size"}
        ):
            errors.append(
                "Menú.metadata.allowed_types debe contener fixed y by_size sin duplicados."
            )

    recommendations = menu["recommendations"]
    recommended_product_ids: list[str] = []
    if require_exact_keys(
        recommendations,
        {"product_ids"},
        "Menú.recommendations",
        errors,
    ):
        raw_recommendations = recommendations["product_ids"]
        if not isinstance(raw_recommendations, list):
            errors.append("Menú.recommendations.product_ids debe ser una lista.")
        else:
            recommended_product_ids = raw_recommendations
            if not 3 <= len(recommended_product_ids) <= 4:
                errors.append(
                    "Menú.recommendations.product_ids debe contener entre 3 y 4 IDs."
                )
            if not all(
                isinstance(product_id, str) and product_id.strip()
                for product_id in recommended_product_ids
            ):
                errors.append(
                    "Menú.recommendations.product_ids solo admite textos no vacíos."
                )
            if len(recommended_product_ids) != len(set(recommended_product_ids)):
                errors.append("Menú.recommendations.product_ids contiene duplicados.")

    products = menu["products"]
    if not isinstance(products, list) or not products:
        errors.append("Menú.products debe ser una lista no vacía.")
        return errors

    product_ids: set[str] = set()
    offering_ids: set[str] = set()
    for product_index, product in enumerate(products):
        product_location = f"Menú.products[{product_index}]"
        if not require_exact_keys(
            product,
            {"product_id", "name", "offerings"},
            product_location,
            errors,
        ):
            continue

        product_id = product["product_id"]
        if not isinstance(product_id, str) or not product_id.strip():
            errors.append(f"{product_location}.product_id debe ser texto no vacío.")
            product_id = ""
        elif product_id in product_ids:
            errors.append(f"Menú: product_id duplicado '{product_id}'.")
        else:
            product_ids.add(product_id)

        if not isinstance(product["name"], str) or not product["name"].strip():
            errors.append(f"{product_location}.name debe ser texto no vacío.")

        offerings = product["offerings"]
        if not isinstance(offerings, list) or not offerings:
            errors.append(f"{product_location}.offerings debe ser una lista no vacía.")
            continue

        for offering_index, offering in enumerate(offerings):
            offering_location = (
                f"{product_location}.offerings[{offering_index}]"
            )
            if not require_exact_keys(
                offering,
                {"offering_id", "menu_section", "price"},
                offering_location,
                errors,
            ):
                continue

            offering_id = offering["offering_id"]
            if not isinstance(offering_id, str) or not offering_id.strip():
                errors.append(f"{offering_location}.offering_id debe ser texto no vacío.")
                offering_id = offering_location
            elif offering_id in offering_ids:
                errors.append(f"Menú: offering_id duplicado '{offering_id}'.")
            else:
                offering_ids.add(offering_id)

            if (
                not isinstance(offering["menu_section"], str)
                or not offering["menu_section"].strip()
            ):
                errors.append(f"{offering_location}.menu_section debe ser texto no vacío.")

            price = offering["price"]
            if not isinstance(price, dict):
                errors.append(f"{offering_location}.price debe ser un objeto.")
                continue

            price_type = price.get("type")
            if price_type == "fixed":
                if require_exact_keys(
                    price,
                    {"type", "amount"},
                    f"{offering_location}.price",
                    errors,
                ) and not is_positive_integer(price["amount"]):
                    errors.append(
                        f"{offering_location}.price.amount debe ser un entero positivo."
                    )
            elif price_type == "by_size":
                if not require_exact_keys(
                    price,
                    {"type", "sizes"},
                    f"{offering_location}.price",
                    errors,
                ):
                    continue
                sizes = price["sizes"]
                if not require_exact_keys(
                    sizes,
                    {"pequeno", "mediano", "grande"},
                    f"{offering_location}.price.sizes",
                    errors,
                ):
                    continue
                if not all(is_positive_integer(value) for value in sizes.values()):
                    errors.append(
                        f"{offering_location}.price.sizes debe contener enteros positivos."
                    )
                elif not sizes["pequeno"] < sizes["mediano"] < sizes["grande"]:
                    errors.append(
                        f"{offering_location}.price.sizes debe crecer de pequeño a grande."
                    )
            else:
                errors.append(
                    f"{offering_location}.price.type debe ser fixed o by_size."
                )

    unknown_recommendations = set(recommended_product_ids) - product_ids
    if unknown_recommendations:
        errors.append(
            "Menú: recomendaciones sin producto declarado: "
            + ", ".join(sorted(unknown_recommendations))
        )

    return errors


class MenuOfferingsJsonValidatorTests(unittest.TestCase):
    def test_menu_offerings_uses_the_current_json_structure(self):
        self.assertEqual(validate(), [])


def main() -> int:
    errors = validate()
    if errors:
        print("menu_offerings.json es inválido:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("menu_offerings.json es válido según su estructura vigente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
