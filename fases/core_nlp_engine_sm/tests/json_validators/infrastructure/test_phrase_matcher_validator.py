"""Pruebas de validación para phrase_matcher_service_config.json."""

import unittest
from tests.json_validators.utils.base_validator import load

class PhraseMatcherValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.phrase_matcher = load("phrase_matcher_service_config.json")

    def test_metadata_structure(self):
        metadata = self.phrase_matcher.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertTrue(set(expected_fields).issubset(set(metadata)), "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")
