"""Pruebas de validación para text_normalizer_service_config.json."""

import unittest
from tests.json_validators.utils.base_validator import load

class TextNormalizerValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = load("text_normalizer_service_config.json")

    def test_metadata_structure(self):
        metadata = self.normalizer.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")

    def test_options_exists(self):
        options = self.normalizer.get("options")
        self.assertIsInstance(options, dict, "falta 'options'.")
