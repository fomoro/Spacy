"""Pruebas de validación para conversation_action_rules.json."""

import unittest
from string import Formatter
from tests.json_validators.utils.base_validator import load, taxonomy_pairs

class ActionRulesValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = load("intents_and_subintents.json")
        cls.valid_pairs = taxonomy_pairs(cls.taxonomy)
        cls.slots = cls.taxonomy.get("slots", {})
        
        cls.conversation_rules = load("conversation_action_rules.json")
        cls.actions = cls.conversation_rules.get("conversation_actions", {})
        cls.rules = cls.conversation_rules.get("rules_by_intent_and_subintent", {})
        cls.questions = cls.conversation_rules.get("questions", {})

    def test_metadata_structure(self):
        metadata = self.conversation_rules.get("metadata", {})
        expected_fields = {
            "schema_version",
            "purpose",
            "language",
            "conversation_action_count",
            "intent_subintent_rule_count",
            "question_count",
        }
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")
        
        self.assertEqual(metadata.get("conversation_action_count"), len(self.actions), "conversation_action_count incorrecto.")
        self.assertEqual(metadata.get("intent_subintent_rule_count"), len(self.rules), "intent_subintent_rule_count incorrecto.")
        self.assertEqual(metadata.get("question_count"), len(self.questions), "question_count incorrecto.")

    def test_top_level_objects(self):
        for field, value in [("conversation_actions", self.actions), ("rules_by_intent_and_subintent", self.rules), ("questions", self.questions)]:
            self.assertIsInstance(value, dict, f"'{field}' debe ser un objeto no vacío.")
            self.assertTrue(value, f"'{field}' debe ser un objeto no vacío.")

    def test_conversation_actions(self):
        expected_categories = {
            "resolved": "successful_resolution",
            "needs_user_clarification": "clarification",
            "needs_transaction_confirmation": "confirmation",
            "needs_business_lookup": "operational_lookup",
            "needs_human_safety_validation": "safety_escalation",
            "needs_human_assistance": "human_escalation",
            "needs_identity_verification": "identity_verification",
            "out_of_scope": "terminal_result",
        }
        self.assertEqual(set(self.actions), set(expected_categories), "El catálogo de acciones no coincide con el contrato.")
        
        for action_id, expected_category in expected_categories.items():
            action = self.actions.get(action_id, {})
            self.assertIsInstance(action, dict, f"'{action_id}' debe ser un objeto.")
            self.assertEqual(set(action), {"category", "requires_clarification_compat", "description"}, f"'{action_id}' contiene campos inesperados.")
            self.assertEqual(action.get("category"), expected_category, f"categoría incorrecta en '{action_id}'.")
            self.assertIsInstance(action.get("requires_clarification_compat"), bool, f"'{action_id}' requiere compatibilidad booleana.")
            self.assertTrue(str(action.get("description", "")).strip(), f"'{action_id}' requiere una descripción.")

    def test_rules_logic(self):
        for pair, policy in self.rules.items():
            self.assertIn(pair, self.valid_pairs, f"regla '{pair}' fuera de la taxonomía.")
            self.assertIsInstance(policy, dict, f"regla '{pair}' debe ser un objeto.")
            
            required = [str(slot) for slot in policy.get("required_slots", [])]
            required_any = [[str(slot) for slot in group] for group in policy.get("required_any", [])]
            
            referenced_slots = set(required)
            for group in required_any:
                referenced_slots.update(group)
            
            unknown_slots = referenced_slots - set(self.slots)
            self.assertFalse(unknown_slots, f"regla '{pair}': slots desconocidos: {unknown_slots}")
            
            for mode_field in ("on_missing", "on_complete"):
                mode = policy.get(mode_field)
                if mode is not None:
                    self.assertIn(mode, self.actions, f"regla '{pair}': acción desconocida '{mode}'.")
            
            question_by_slot = policy.get("question_by_slot", {})
            expected_question_slots = set(required) | {"|".join(group) for group in required_any if group}
            missing = expected_question_slots - set(question_by_slot)
            self.assertFalse(missing, f"regla '{pair}': faltan preguntas para {missing}")
            
            requires_identity = policy.get("requires_identity_verification")
            if requires_identity is not None:
                self.assertIsInstance(requires_identity, bool, f"regla '{pair}': requires_identity_verification debe ser booleano.")
            if requires_identity is True:
                self.assertIn("needs_identity_verification", self.actions, "falta declarar needs_identity_verification.")

    def test_questions(self):
        allowed_placeholders = set(self.slots) | {"options"}
        for question_key, question in self.questions.items():
            self.assertIsInstance(question, dict)
            self.assertTrue(str(question.get("template", "")).strip(), f"pregunta '{question_key}' sin template.")
            
            for text_field in ("template", "fallback"):
                text = question.get(text_field)
                if text is None:
                    continue
                try:
                    placeholders = {name for _, name, _, _ in Formatter().parse(str(text)) if name}
                except ValueError as exc:
                    self.fail(f"formato inválido en '{question_key}': {exc}.")
                
                unknown = placeholders - allowed_placeholders
                self.assertFalse(unknown, f"'{question_key}' usa slots desconocidos: {unknown}")
