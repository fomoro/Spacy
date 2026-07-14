from pathlib import Path
"""Pruebas unitarias de PhraseMatcherService."""

import unittest

from src.infrastructure import TextNormalizer, PhraseMatcherService


ROOT = Path(__file__).resolve().parents[2]


class PhraseMatcherServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
        cls.matcher = PhraseMatcherService(
            ROOT / "resources" / "menu" / "menu_catalog.json"
        )

    def entities(self, text: str):
        normalized = self.normalizer.normalize(text).normalized
        return self.matcher.match(normalized).entities

    def test_specific_product_wins_over_generic_product(self):
        entities = self.entities("¿Cuánto vale la mojarra frita?")
        self.assertTrue(
            any(
                e.entity_type == "PRODUCTO_ESPECIFICO"
                and e.entity_id == "mojarra_frita"
                for e in entities
            )
        )
        self.assertFalse(
            any(
                e.entity_type == "PRODUCTO_BASE"
                and e.entity_id == "mojarra"
                for e in entities
            )
        )

    def test_generic_product_is_not_forced_to_specific_menu_item(self):
        entities = self.entities("¿Cuánto vale la mojarra?")
        self.assertTrue(
            any(
                e.entity_type == "PRODUCTO_BASE"
                and e.entity_id == "mojarra"
                for e in entities
            )
        )
        self.assertFalse(
            any(e.entity_type == "PRODUCTO_ESPECIFICO" for e in entities)
        )

    def test_category(self):
        entities = self.entities("¿Qué arroces tienen?")
        self.assertTrue(
            any(e.entity_type == "CATEGORIA" and e.entity_id == "arroces"
                for e in entities)
        )
