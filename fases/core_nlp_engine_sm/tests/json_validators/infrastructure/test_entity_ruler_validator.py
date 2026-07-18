"""Pruebas de validación para entity_ruler_service_config.json."""

import unittest
from tests.json_validators.utils.base_validator import load

class EntityRulerValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entity_ruler = load("entity_ruler_service_config.json")

    def test_metadata_structure(self):
        metadata = self.entity_ruler.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertTrue(set(expected_fields).issubset(set(metadata)), "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")
