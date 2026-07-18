"""Pruebas de validación para matcher_service_config.json."""

import json
import unittest
from tests.json_validators.utils.base_validator import load

class MatcherValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matcher = load("matcher_service_config.json")

    def test_metadata_structure(self):
        metadata = self.matcher.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")

    def test_patterns(self):
        pattern_ids = set()
        for pattern in self.matcher.get("patterns", []):
            rule_id = str(pattern.get("id", ""))
            self.assertTrue(rule_id, "hay una regla sin id.")
            self.assertNotIn(rule_id, pattern_ids, f"Matcher: id duplicado '{rule_id}'.")
            pattern_ids.add(rule_id)
            
            unexpected = set(pattern) - {"id", "pattern", "full_text_only"}
            self.assertFalse(unexpected, f"Matcher: '{rule_id}' contiene llaves desconocidas: {unexpected}")
            
            self.assertIsInstance(pattern.get("pattern"), list, f"Matcher: '{rule_id}' el patrón debe ser una lista.")
            self.assertIsInstance(pattern.get("full_text_only", False), bool, f"Matcher: '{rule_id}' full_text_only debe ser booleano.")
            
            serialized_pattern = json.dumps(pattern.get("pattern"), ensure_ascii=False)
            self.assertNotIn("intent", serialized_pattern, f"Matcher: '{rule_id}' contiene decisiones que no pertenecen a infraestructura.")
            self.assertNotIn("ENT_TYPE", serialized_pattern, f"Matcher: '{rule_id}' todavía depende de entidades previas.")
            self.assertNotIn("ENT_ID", serialized_pattern, f"Matcher: '{rule_id}' todavía depende de entidades previas.")
