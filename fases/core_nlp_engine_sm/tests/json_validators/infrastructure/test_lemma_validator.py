"""Pruebas de validación para lemma_service_config.json."""

import unittest
from tests.json_validators.utils.base_validator import load

class LemmaValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lemmas = load("lemma_service_config.json")

    def test_metadata_structure(self):
        metadata = self.lemmas.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")

    def test_options(self):
        lemma_options = self.lemmas.get("options", {})
        self.assertIsInstance(lemma_options, dict)
        self.assertEqual(set(lemma_options), {"minimum_token_length", "ignored_pos"}, "options no coincide con el contrato.")
        
        self.assertIsInstance(lemma_options.get("minimum_token_length"), int, "options.minimum_token_length debe ser entero.")
        
        ignored_pos = lemma_options.get("ignored_pos")
        self.assertIsInstance(ignored_pos, list)
        self.assertTrue(all(isinstance(value, str) and value for value in ignored_pos), "options.ignored_pos debe ser una lista de textos.")

    def test_signals(self):
        lemma_ids = set()
        for signal in self.lemmas.get("signals", []):
            lemma_id = str(signal.get("lemma", ""))
            lemma_ids.add(lemma_id)
            self.assertEqual(set(signal), {"lemma", "forms"}, f"Lemma: '{lemma_id}' contiene decisiones que no pertenecen a infraestructura.")
