from pathlib import Path
import unittest

from src.infrastructure import TextNormalizer, PhraseMatcherService, MatcherService, LemmaService, EntityRulerService
from src.application import LinguisticParser

ROOT = Path(__file__).resolve().parents[2]


class EntityRulerServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = TextNormalizer(ROOT / "resources" / "rules_config.json")
        cls.phrase_matcher = PhraseMatcherService(ROOT / "resources" / "menu_catalog.json")
        cls.matcher = MatcherService(ROOT / "resources" / "rules_config.json", cls.phrase_matcher)
        cls.lemmas = LemmaService(ROOT / "resources" / "rules_config.json")
        cls.ruler = EntityRulerService(ROOT / "resources" / "rules_config.json")
        cls.parser = LinguisticParser(cls.normalizer, cls.phrase_matcher, cls.matcher, cls.lemmas, cls.ruler)

    def test_ruler_extracts_weekday(self) -> None:
        entities = self.ruler.match("¿Qué promociones tienen el lunes?")
        weekday_ents = [ent for ent in entities if ent["entity_type"] == "DIA_SEMANA"]
        self.assertTrue(weekday_ents)
        self.assertEqual(weekday_ents[0]["entity_id"], "lunes")

    def test_ruler_extracts_context_reference(self) -> None:
        entities = self.ruler.match("mándeme el menú otra vez")
        context_ents = [ent for ent in entities if ent["entity_type"] == "REFERENCIA_CONTEXTUAL"]
        self.assertTrue(context_ents)
        self.assertEqual(context_ents[0]["entity_id"], "ultimo_elemento")

    def test_parser_integrates_ruler_entities(self) -> None:
        bundle = self.parser.analyze("quiero mojarra el martes otra vez")
        entities = bundle.phrase_matcher["entities"]
        
        # Debe contener la mojarra (de PhraseMatcherService)
        self.assertTrue(any(ent["entity_id"] == "mojarra" for ent in entities))
        # Debe contener el martes (de EntityRulerService a través del puente de compatibilidad)
        self.assertTrue(any(ent["entity_id"] == "martes" for ent in entities))
        # Debe contener otra vez (de EntityRulerService a través del puente de compatibilidad)
        self.assertTrue(any(ent["entity_id"] == "ultimo_elemento" for ent in entities))


if __name__ == "__main__":
    unittest.main()
