"""Pruebas de orquestación de LinguisticParser."""

from pathlib import Path
import unittest

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizerService
from src.temp import LinguisticEvidenceMapper
from src.temp import LinguisticParser

ROOT = Path(__file__).resolve().parents[3]


class LinguisticParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
        phrase = PhraseMatcherService(
            ROOT
            / "src"
            / "infrastructure"
            / "resources"
            / "phrase_matcher_service_config.json"
        )
        matcher = MatcherService(ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json")
        lemmas = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")
        ruler = EntityRulerService(ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json")
        evidence_mapper = LinguisticEvidenceMapper(ROOT / "src" / "temp" / "resources" / "intent_resolver" / "linguistic_evidence_mapping.json")
        cls.pipeline = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler, evidence_mapper)

    def test_integrated_price_analysis(self):
        result = self.pipeline.analyze("cuanto balen la mojarra frita")
        self.assertIn("valen", result.normalized_text)
        self.assertTrue(result.phrase_matcher["entities"])
        self.assertTrue(result.lemmas["evidence"])

    def test_pipeline_does_not_resolve_final_intent(self):
        result = self.pipeline.analyze("Quiero saber cuánto vale la mojarra")
        payload = result.to_dict()
        self.assertNotIn("final_intent", payload)
        self.assertIn("matcher", payload)
        self.assertIn("lemmas", payload)
        self.assertIn("entity_ruler", payload)


if __name__ == "__main__":
    unittest.main()
