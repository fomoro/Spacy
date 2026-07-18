"""Pruebas de validación para conversation_profiles.json y perfiles."""

import json
import unittest
from tests.json_validators.utils.base_validator import load, CONVERSATION_PATHS

class ConversationProfilesValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = load("conversation_profiles.json")

    def test_conversation_messages_structure(self):
        conversation_messages = set()
        
        for conversation_name, conversation_path in CONVERSATION_PATHS.items():
            if not conversation_path.is_file():
                self.fail(f"Faltan recursos: {conversation_name}")
                
            conversation = json.loads(conversation_path.read_text(encoding="utf-8"))
            
            self.assertIsInstance(conversation, list, f"Conversación {conversation_name}: debe ser una lista de cinco mensajes.")
            self.assertEqual(len(conversation), 5, f"Conversación {conversation_name}: debe ser una lista de cinco mensajes.")
            
            self.assertTrue(
                all(isinstance(message, str) and message.strip() for message in conversation),
                f"Conversación {conversation_name}: todos los elementos deben ser textos no vacíos."
            )
            
            normalized = {" ".join(message.casefold().split()) for message in conversation}
            self.assertEqual(len(normalized), 5, f"Conversación {conversation_name}: contiene mensajes duplicados.")
            
            overlap = conversation_messages.intersection(normalized)
            self.assertFalse(overlap, f"Conversación {conversation_name}: repite mensajes de otro flujo.")
            
            conversation_messages.update(normalized)
