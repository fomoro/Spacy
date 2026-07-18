"""Script interactivo para probar el motor NLP."""

import json
from pathlib import Path

from src.infrastructure.nlp.text_normalizer_service import TextNormalizerService
from src.infrastructure.nlp.phrase_matcher_service import PhraseMatcherService
from src.infrastructure.nlp.matcher_service import MatcherService
from src.infrastructure.nlp.lemma_service import LemmaService
from src.infrastructure.nlp.entity_ruler_service import EntityRulerService
from src.application.linguistic_parser import LinguisticParser
from src.application.linguistic_evidence_mapper import LinguisticEvidenceMapper
from src.domain.intent_resolver import IntentResolver
from src.application.response_renderer import ResponseRenderer
from src.application.dialogue_orchestrator import DialogueOrchestrator

ROOT = Path(__file__).resolve().parent

print("Cargando el cerebro del bot (Spacy y JSONs)...")

# 1. Instanciar Infraestructura
normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
phrase = PhraseMatcherService(ROOT / "src" / "infrastructure" / "resources" / "phrase_matcher_service_config.json")
matcher = MatcherService(ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json")
lemmas = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")
ruler = EntityRulerService(ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json")

# 2. Ensamblar Parser
parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)

# 3. Ensamblar Lógica de Aplicación y Dominio
evidence_mapper = LinguisticEvidenceMapper(ROOT / "src" / "application" / "resources" / "linguistic_evidence_mapping.json")
resolver = IntentResolver(ROOT / "src" / "domain" / "resources")
response_renderer = ResponseRenderer(ROOT / "src" / "application" / "resources" / "response_templates.json")

# 4. Orquestador
bot = DialogueOrchestrator(parser, evidence_mapper, resolver, response_renderer)

print("¡Bot listo!")
print("-" * 50)
print("Escribe un mensaje para el bot (o 'salir' para terminar).\n")

while True:
    try:
        user_input = input("Tú: ")
        if user_input.strip().lower() in ("salir", "exit", "quit"):
            break
        
        if not user_input.strip():
            continue

        # El bot procesa el mensaje
        result = bot.analyze(user_input)
        
        # Obtenemos la intención detectada
        intent_detected = f"{result.resolution.intent}.{result.resolution.subintent}"
        
        # Obtenemos el mensaje renderizado
        bot_response = result.response.text
        
        print(f"\n[Intención detectada]: {intent_detected}")
        print(f"Bot: {bot_response}\n")
        print("-" * 50)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"\n[Error processing message]: {e}\n")
