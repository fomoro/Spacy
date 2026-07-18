"""Pruebas de la traducción de señales neutrales a evidencia del dominio."""

from pathlib import Path
import unittest

from src.temp import LinguisticEvidenceMapper, ParsedNLPBundle


ROOT = Path(__file__).resolve().parents[3]


class LinguisticEvidenceMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mapper = LinguisticEvidenceMapper(
            ROOT
            / "src"
            / "temp"
            / "resources"
            / "intent_resolver"
            / "linguistic_evidence_mapping.json"
        )

    @staticmethod
    def sections(*, with_product: bool = True):
        entities = []
        if with_product:
            entities.append(
                {
                    "entity_type": "PRODUCTO_ESPECIFICO",
                    "entity_id": "mojarra_frita",
                    "canonical": "Mojarra frita",
                    "text": "mojarra",
                    "start_char": 20,
                    "end_char": 27,
                    "start_token": 4,
                    "end_token": 5,
                }
            )
        return {
            "phrase_matcher": {
                "text": "cuánto vale la mojarra",
                "entities": entities,
                "discarded_overlaps": [],
            },
            "matcher": {
                "text": "cuánto vale la mojarra",
                "signals": [
                    {
                        "rule_id": "PRICE_Q_WH",
                        "text": "cuánto vale la",
                        "start_token": 0,
                        "end_token": 3,
                    }
                ],
                "extraction": {
                    "quantities": [],
                    "monetary_values": [],
                    "has_negation": False,
                    "referenced_entities": [],
                },
            },
            "lemmas": {
                "text": "cuánto vale la mojarra",
                "tokens": [],
                "signals": [
                    {
                        "lemma": "valer",
                        "matched_text": "vale",
                        "token_index": 1,
                        "source": "catalog_fallback",
                    }
                ],
                "model_has_lemmatizer": False,
            },
            "entity_ruler": {"text": "cuánto vale la mojarra", "entities": []},
        }

    def test_combines_syntactic_signal_with_required_product(self):
        mapped = self.mapper.map_sections(**self.sections())
        evidence = mapped["matcher"]["evidence"]
        self.assertTrue(evidence)
        self.assertEqual(evidence[0]["intent"], "precio")
        self.assertEqual(evidence[0]["subintent"], "consultar_precio_producto")

    def test_rejects_composite_rule_without_required_entity(self):
        mapped = self.mapper.map_sections(**self.sections(with_product=False))
        self.assertEqual(mapped["matcher"]["evidence"], [])

    def test_rejects_entity_too_far_from_syntactic_signal(self):
        sections = self.sections()
        sections["phrase_matcher"]["entities"][0]["start_token"] = 20
        sections["phrase_matcher"]["entities"][0]["end_token"] = 21
        mapped = self.mapper.map_sections(**sections)
        self.assertEqual(mapped["matcher"]["evidence"], [])

    def test_maps_lemma_outside_infrastructure(self):
        mapped = self.mapper.map_sections(**self.sections())
        evidence = mapped["lemmas"]["evidence"]
        self.assertTrue(evidence)
        self.assertEqual(evidence[0]["intent"], "precio")
        self.assertEqual(evidence[0]["lemma"], "valer")

    def test_preserves_entities_in_application_bundle(self):
        mapped = self.mapper.map_sections(**self.sections())
        referenced = mapped["matcher"]["extraction"]["referenced_entities"]
        self.assertEqual(referenced[0]["entity_id"], "mojarra_frita")

    def test_accepts_mapping_dictionary_as_configuration(self):
        mapper = LinguisticEvidenceMapper(self.mapper.config)
        mapped = mapper.map_sections(**self.sections())
        self.assertTrue(mapped["matcher"]["evidence"])

    def test_translates_a_parsed_bundle_without_owning_the_parser(self):
        sections = self.sections()
        parsed_bundle = ParsedNLPBundle(
            original_text="¿Cuánto vale la mojarra?",
            normalized_text="cuánto vale la mojarra",
            normalization={"normalized": "cuánto vale la mojarra"},
            **sections,
        )

        evidence = self.mapper.map_bundle(parsed_bundle)

        self.assertEqual(evidence.original_text, "¿Cuánto vale la mojarra?")
        self.assertTrue(evidence.matcher["evidence"])

    def test_rejects_an_invalid_parsed_bundle(self):
        with self.assertRaisesRegex(TypeError, "ParsedNLPBundle"):
            self.mapper.map_bundle({})


if __name__ == "__main__":
    unittest.main()
