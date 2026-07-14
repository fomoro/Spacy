import json
from pathlib import Path
import unittest

from src.application import IntentResolver
from src.infrastructure import LemmaService, MatcherService, PhraseMatcherService, TextNormalizer


ROOT = Path(__file__).resolve().parents[1]


class ConfigurationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = json.loads((ROOT / "resources" / "nlp" / "normalizer_config.json").read_text(encoding="utf-8"))
        cls.matcher = json.loads((ROOT / "resources" / "nlp" / "matcher_patterns.json").read_text(encoding="utf-8"))
        cls.lemmas = json.loads((ROOT / "resources" / "nlp" / "lemma_signals.json").read_text(encoding="utf-8"))
        cls.resolver = json.loads((ROOT / "resources" / "nlp" / "resolver_config.json").read_text(encoding="utf-8"))
        cls.clarification = json.loads(
            (ROOT / "resources" / "dialogue" / "clarification_policy.json").read_text(encoding="utf-8")
        )
        cls.menu = json.loads(
            (ROOT / "resources" / "menu" / "menu_catalog.json").read_text(encoding="utf-8")
        )

    def test_services_accept_section_dictionaries(self):
        normalizer = TextNormalizer(self.normalizer)
        phrase = PhraseMatcherService(self.menu)
        matcher = MatcherService(self.matcher, phrase)
        lemmas = LemmaService(self.lemmas)
        resolver = IntentResolver(self.resolver, self.clarification)

        self.assertEqual(normalizer.normalize("  HOLA  ").normalized, "hola")
        self.assertIn("entity_types", phrase.catalog)
        self.assertIn("patterns", matcher.catalog)
        self.assertIn("signals", lemmas.catalog)
        self.assertIn("thresholds", resolver.config)
        self.assertIn("policies", resolver.clarification_policy)


if __name__ == "__main__":
    unittest.main()
