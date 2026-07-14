"""Pruebas de construcción de servicios desde recursos declarativos."""

import json
from pathlib import Path
import unittest

from src.infrastructure import LemmaService, MatcherService, PhraseMatcherService, TextNormalizer


ROOT = Path(__file__).resolve().parents[2]


class ConfigurationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = json.loads((ROOT / "resources" / "nlp" / "normalizer_config.json").read_text(encoding="utf-8"))
        cls.matcher = json.loads((ROOT / "resources" / "nlp" / "matcher_patterns.json").read_text(encoding="utf-8"))
        cls.lemmas = json.loads((ROOT / "resources" / "nlp" / "lemma_signals.json").read_text(encoding="utf-8"))
        cls.menu = json.loads(
            (ROOT / "resources" / "menu" / "menu_catalog.json").read_text(encoding="utf-8")
        )

    def test_services_accept_section_dictionaries(self):
        normalizer = TextNormalizer(self.normalizer)
        phrase = PhraseMatcherService(self.menu)
        matcher = MatcherService(self.matcher, phrase)
        lemmas = LemmaService(self.lemmas)

        self.assertEqual(normalizer.normalize("  HOLA  ").normalized, "hola")
        self.assertIn("entity_types", phrase.catalog)
        self.assertIn("patterns", matcher.catalog)
        self.assertIn("signals", lemmas.catalog)


if __name__ == "__main__":
    unittest.main()
