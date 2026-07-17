"""Pruebas de composición de respuestas sin duplicar datos de negocio."""

from pathlib import Path
import unittest

from src.temp import ResponseComposer


ROOT = Path(__file__).resolve().parents[3]


class ResponseComposerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.composer = ResponseComposer(
            ROOT / "src" / "temp" / "resources" / "response_templates.json",
            ROOT
            / "resources"
            / "business_data"
            / "restaurant"
            / "restaurant_profile.json",
        )

    def test_uses_restaurant_profile_for_stable_business_data(self):
        response = self.composer.render("greeting")
        self.assertIn("Mar Azul del Pacífico", response)

    def test_dynamic_commercial_data_must_be_supplied_by_caller(self):
        with self.assertRaisesRegex(ValueError, "menu_summary"):
            self.composer.render("menu")
        response = self.composer.render("menu", {"menu_summary": "arroces y pescados"})
        self.assertIn("arroces y pescados", response)

    def test_payment_methods_come_from_business_profile(self):
        response = self.composer.render("payment_methods")
        self.assertIn("nequi", response)
        self.assertIn("pago qr", response)

    def test_unknown_template_is_rejected(self):
        with self.assertRaises(KeyError):
            self.composer.render("does_not_exist")


if __name__ == "__main__":
    unittest.main()
