"""Valida de forma independiente la estructura vigente de restaurant_profile.json."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    ROOT
    / "resources"
    / "business_data"
    / "restaurant"
    / "restaurant_profile.json"
)
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


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


def is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate() -> list[str]:
    errors: list[str] = []
    if not PROFILE_PATH.is_file():
        return [f"No existe el perfil del restaurante: {PROFILE_PATH}"]

    try:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"No se pudo leer restaurant_profile.json: {exc}"]

    if not require_exact_keys(
        profile,
        {"metadata", "restaurant"},
        "Perfil",
        errors,
    ):
        return errors

    metadata = profile["metadata"]
    if require_exact_keys(
        metadata,
        {"schema_version", "purpose", "language", "domain"},
        "Perfil.metadata",
        errors,
    ):
        if metadata["schema_version"] != "2.0.0":
            errors.append("Perfil.metadata.schema_version debe ser '2.0.0'.")
        if not is_non_empty_text(metadata["purpose"]):
            errors.append("Perfil.metadata.purpose debe ser texto no vacío.")
        if metadata["language"] != "es-CO":
            errors.append("Perfil.metadata.language debe ser 'es-CO'.")
        if not is_non_empty_text(metadata["domain"]):
            errors.append("Perfil.metadata.domain debe ser texto no vacío.")

    restaurant = profile["restaurant"]
    if not require_exact_keys(
        restaurant,
        {
            "name",
            "description",
            "address",
            "timezone",
            "opening_hours",
            "payment_methods",
        },
        "Perfil.restaurant",
        errors,
    ):
        return errors

    for field in ("name", "description"):
        if not is_non_empty_text(restaurant[field]):
            errors.append(f"Perfil.restaurant.{field} debe ser texto no vacío.")

    address = restaurant["address"]
    if require_exact_keys(
        address,
        {"street", "neighborhood", "city", "country"},
        "Perfil.restaurant.address",
        errors,
    ):
        for field in ("street", "neighborhood", "city", "country"):
            if not is_non_empty_text(address[field]):
                errors.append(
                    f"Perfil.restaurant.address.{field} debe ser texto no vacío."
                )

    if restaurant["timezone"] != "America/Bogota":
        errors.append("Perfil.restaurant.timezone debe ser 'America/Bogota'.")

    opening_hours = restaurant["opening_hours"]
    if require_exact_keys(
        opening_hours,
        DAYS,
        "Perfil.restaurant.opening_hours",
        errors,
    ):
        for day in sorted(DAYS):
            schedule = opening_hours[day]
            location = f"Perfil.restaurant.opening_hours.{day}"
            if not isinstance(schedule, dict):
                errors.append(f"{location} debe ser un objeto.")
                continue
            keys = set(schedule)
            if keys == {"closed"}:
                if schedule["closed"] is not True:
                    errors.append(f"{location}.closed debe ser true.")
                continue
            if keys != {"open", "close"}:
                errors.append(
                    f"{location} debe declarar closed o el par open/close."
                )
                continue
            opening = schedule["open"]
            closing = schedule["close"]
            if not isinstance(opening, str) or not TIME_PATTERN.fullmatch(opening):
                errors.append(f"{location}.open debe usar el formato HH:MM.")
            if not isinstance(closing, str) or not TIME_PATTERN.fullmatch(closing):
                errors.append(f"{location}.close debe usar el formato HH:MM.")
            if (
                isinstance(opening, str)
                and isinstance(closing, str)
                and TIME_PATTERN.fullmatch(opening)
                and TIME_PATTERN.fullmatch(closing)
                and opening >= closing
            ):
                errors.append(f"{location}.open debe ser anterior a close.")

    payment_methods = restaurant["payment_methods"]
    if not isinstance(payment_methods, list) or not payment_methods:
        errors.append("Perfil.restaurant.payment_methods debe ser una lista no vacía.")
    else:
        if not all(is_non_empty_text(method) for method in payment_methods):
            errors.append(
                "Perfil.restaurant.payment_methods solo admite textos no vacíos."
            )
        if len(payment_methods) != len(set(payment_methods)):
            errors.append("Perfil.restaurant.payment_methods contiene duplicados.")

    return errors


class RestaurantProfileJsonValidatorTests(unittest.TestCase):
    def test_restaurant_profile_uses_the_current_json_structure(self):
        self.assertEqual(validate(), [])


def main() -> int:
    errors = validate()
    if errors:
        print("restaurant_profile.json es inválido:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("restaurant_profile.json es válido según su estructura vigente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
