import json
import os
import time
from pathlib import Path

# NOTA: Debes instalar la librería de Gemini o OpenAI según tu preferencia.
# pip install google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Por favor instala el SDK de Gemini: pip install google-genai")
    exit(1)

# Configuración
# Asegúrate de configurar tu variable de entorno GEMINI_API_KEY en la terminal antes de correr esto:
# set GEMINI_API_KEY="tu-llave-aqui"
client = genai.Client()

BASE_DIR = Path(r"c:\Dev\GitHub\Spacy\fases\core_nlp_engine_sm\resources\corpus")
BENCHMARK_PATH = BASE_DIR / "benchmarks" / "customer_intent_benchmark.json"
PROFILES_PATH = BASE_DIR / "profiles" / "conversation_profiles.json"
OUTPUT_PATH = BASE_DIR / "benchmarks" / "customer_intent_benchmark_natural.json"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def main():
    print("Cargando archivos...")
    benchmark = load_json(BENCHMARK_PATH)
    profiles_data = load_json(PROFILES_PATH)
    
    # Crear un diccionario rápido de perfiles
    profiles = {p["id"]: p for p in profiles_data.get("profiles", [])}
    
    cases = benchmark.get("cases", [])
    total_cases = len(cases)
    
    print(f"Iniciando reescritura de {total_cases} casos...")
    
    for i, case in enumerate(cases):
        # Si la frase ya suena natural o no quieres gastar tokens en todas, podrías poner un if aquí.
        original_message = case.get("message", "")
        profile_id = case.get("profile_id")
        expected = case.get("expected", {})
        entities = case.get("expected_entities", [])
        
        profile = profiles.get(profile_id, {})
        profile_desc = profile.get("description", "")
        linguistic_features = "\n".join(f"- {f}" for f in profile.get("linguistic_features", []))
        
        # Construir el Prompt
        prompt = f"""
Eres un filólogo experto en el español de Colombia.
Tu tarea es reescribir la siguiente frase artificial para que suene 100% natural, manteniendo exactamente la misma intención y las entidades clave.

Frase original (muy robótica/concatenada): "{original_message}"

Intención de fondo: {expected.get('intent')}.{expected.get('subintent')}
Entidades obligatorias que DEBEN permanecer en el texto: {[e.get('entity_id') or e.get('entity_type') for e in entities]}

Perfil Lingüístico del hablante:
{profile_desc}
Rasgos lingüísticos que DEBES incorporar sutilmente:
{linguistic_features}

REGLAS:
1. Responde ÚNICAMENTE con la frase reescrita. No agregues comillas, ni explicaciones, ni texto extra.
2. La frase debe fluir como si un colombiano real la estuviera escribiendo por WhatsApp o diciéndola en un restaurante.
3. NO elimines la ambigüedad si la frase original estaba pidiendo o preguntando algo específico.
"""
        
        try:
            print(f"[{i+1}/{total_cases}] Procesando {case['id']} ({profile_id})...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            new_message = response.text.strip().replace('"', '')
            
            # Actualizar el caso
            case["message"] = new_message
            
            # Guardar progresivamente cada 10 casos por si se cae el script
            if (i + 1) % 10 == 0:
                save_json(benchmark, OUTPUT_PATH)
                
            time.sleep(1) # Pequeña pausa para no saturar los límites de la API (rate limit)
            
        except Exception as e:
            print(f"Error procesando el caso {case['id']}: {e}")
            # Guardamos lo que llevamos y salimos para no perder el trabajo
            save_json(benchmark, OUTPUT_PATH)
            break
            
    # Guardado final
    save_json(benchmark, OUTPUT_PATH)
    print(f"\n¡Proceso completado! El archivo naturalizado se guardó en:\n{OUTPUT_PATH}")
    print("Revisa los resultados, y si te gustan, puedes reemplazar el archivo original.")

if __name__ == "__main__":
    main()
