# ============================================
# 1. IMPORTACIONES
# ============================================
import spacy
import re
import sys
import os

# Agregar el directorio actual al path para importar utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import cargar_json, formatear_precio

# ============================================
# 2. CARGA DE DATOS
# ============================================
config = cargar_json("config.json")
RESPUESTAS = cargar_json("respuestas.json")
PATRONES_CLAVE = cargar_json("patrones_clave.json")
FRASES_CLAVE = cargar_json("frases_clave.json")
PRODUCTOS = cargar_json("productos.json")

# ============================================
# 3. CONFIGURACIÓN
# ============================================
MODELO_SPACY = config.get("modelo_spacy", "es_core_news_sm")
NOMBRE_RESTAURANTE = config.get("nombre_restaurante", "Mar Azul del Pacífico")
MENSAJE_BIENVENIDA = config.get("mensaje_bienvenida", f"¡Bienvenido a {NOMBRE_RESTAURANTE}! 🐟")

# ============================================
# 4. CARGA DE SPACY
# ============================================
try:
    nlp = spacy.load(MODELO_SPACY)
except OSError:
    print(f"⚠️ Error: Modelo '{MODELO_SPACY}' no encontrado. Instalando...")
    os.system(f"python -m spacy download {MODELO_SPACY}")
    nlp = spacy.load(MODELO_SPACY)

# ============================================
# 5. FUNCIONES DEL BOT
# ============================================

def detectar_intencion(texto):
    """
    Detecta la intención del usuario usando 3 estrategias:
    1. Patrones regex (más rápido)
    2. Frases exactas
    3. spaCy (lemas)
    """
    texto_limpio = texto.lower().strip()
    
    # --- ESTRATEGIA 1: Patrones regex ---
    for intencion, patrones in PATRONES_CLAVE.items():
        for patron in patrones:
            try:
                if re.search(patron, texto_limpio, re.IGNORECASE):
                    return intencion
            except re.error:
                continue
    
    # --- ESTRATEGIA 2: Frases exactas ---
    for intencion, frases in FRASES_CLAVE.items():
        for frase in frases:
            if frase.lower() in texto_limpio:
                return intencion
    
    # --- ESTRATEGIA 3: spaCy (lemas) ---
    doc = nlp(texto_limpio)
    lemas = [token.lemma_.lower() for token in doc]
    
    # Mapeo de palabras clave por intención
    palabras_por_intencion = {
        "menu": ["menú", "carta", "comida", "ofrecer", "vender", 
                 "pescado", "arroces", "cazuela", "marisco", 
                 "camaron", "langostino", "ceviche", "almuerzo", 
                 "ejecutivo"],
        "precio": ["precio", "costo", "valor", "cuánto", "vale", "cuesta"],
        "ubicacion": ["ubicación", "dirección", "dónde", "local", "encuentro"],
        "horario": ["horario", "hora", "abrir", "cerrar", "atienden"],
        "pago": ["pago", "pagar", "tarjeta", "efectivo", "nequi", "daviplata"],
        "pedido": ["pedir", "ordenar", "comprar", "deseo", "quiero"],
        "saludo": ["hola", "buen", "día", "tarde", "noche", "saludo"],
        "gracias": ["gracias", "agradecer", "agradecido"]
    }
    
    for intencion, palabras in palabras_por_intencion.items():
        for palabra in palabras:
            if palabra in lemas:
                return intencion
    
    return "desconocido"

def obtener_producto(texto):
    """
    Extrae el nombre del producto del texto del usuario
    """
    texto_limpio = texto.lower().strip()
    productos = [
        "mojarra", "bagre", "salmón", "trucha", "sierra", "pargo",
        "mapará", "lenguado", "robalo", "bocachico", "capaz", "camarones",
        "langostinos", "ceviche", "arroz", "cazuela", "filete", "sancocho",
        "churrasco"
    ]
    
    for producto in productos:
        if producto in texto_limpio:
            return producto
    return None

def obtener_preparacion(texto):
    """
    Extrae la preparación del texto del usuario
    """
    texto_limpio = texto.lower().strip()
    preparaciones = [
        "frito", "frita", "en salsa", "al horno", "sudada", "dorado",
        "al ajillo", "a la marinera", "apanado", "a la plancha", "al vapor"
    ]
    
    for preparacion in preparaciones:
        if preparacion in texto_limpio:
            return preparacion
    return None

def generar_respuesta(intencion, texto_usuario=None):
    """
    Genera la respuesta del bot para una intención dada
    """
    # Obtener respuesta base
    respuesta_base = RESPUESTAS.get(intencion, RESPUESTAS.get("desconocido", "No entendí tu mensaje."))
    
    # Personalizar según la intención
    if intencion == "productos_especificos" and texto_usuario:
        producto = obtener_producto(texto_usuario)
        preparacion = obtener_preparacion(texto_usuario)
        
        if producto and preparacion:
            respuesta_base = respuesta_base.replace("{producto}", producto)
            respuesta_base = respuesta_base.replace("{preparacion}", preparacion)
        elif producto:
            respuesta_base = f"Sí, tenemos {producto}. ¿Te gustaría saber el precio o hacer un pedido?"
    
    elif intencion == "precio" and texto_usuario:
        producto = obtener_producto(texto_usuario)
        if producto:
            # Buscar el precio en el menú
            precio = None
            for categoria in PRODUCTOS.get("categorias", {}).values():
                for prod_key, prod_data in categoria.get("productos", {}).items():
                    if producto in prod_data.get("nombre", "").lower():
                        precio = prod_data.get("precio")
                        break
                if precio:
                    break
            
            if precio:
                if isinstance(precio, str):
                    respuesta_base = f"El {producto} tiene precio según tamaño. ¿Te gustaría más información?"
                else:
                    precio_formateado = formatear_precio(precio)
                    respuesta_base = f"El {producto} cuesta ${precio_formateado}. ¿Te gustaría pedirlo?"
            else:
                respuesta_base = f"No encontramos el precio de {producto}. ¿Puedes ser más específico?"
    
    return respuesta_base

def procesar_mensaje(texto_usuario):
    """
    Procesa el mensaje completo del usuario
    """
    intencion = detectar_intencion(texto_usuario)
    respuesta = generar_respuesta(intencion, texto_usuario)
    return respuesta

# ============================================
# 6. PROGRAMA PRINCIPAL
# ============================================

def ejecutar_chat():
    """
    Ejecuta el chat principal
    """
    print("=" * 50)
    print(MENSAJE_BIENVENIDA)
    print("=" * 50)
    print("Escribe 'chao' para salir")
    print("Escribe 'ayuda' para ver qué puedo hacer")
    print("-" * 50)
    
    while True:
        mensaje_usuario = input("\nTú: ").strip()
        
        # Verificar si quiere salir
        if mensaje_usuario.lower() in ["chao", "adiós", "bye", "salir", "exit"]:
            print("Bot:", RESPUESTAS.get("despedida", "¡Hasta luego!"))
            break
        
        # Verificar si quiere ayuda
        if mensaje_usuario.lower() == "ayuda":
            print("Bot: Puedo ayudarte con:")
            print("  - Menú y productos")
            print("  - Precios")
            print("  - Ubicación y horario")
            print("  - Formas de pago")
            print("  - Hacer pedidos")
            print("  - Recomendaciones")
            continue
        
        # Verificar si ingresó algo
        if not mensaje_usuario:
            print("Bot: Por favor, escribe algo para poder ayudarte")
            continue
        
        # Procesar y mostrar respuesta
        respuesta_bot = procesar_mensaje(mensaje_usuario)
        print("Bot:", respuesta_bot)

# ============================================
# 7. PUNTO DE ENTRADA
# ============================================

if __name__ == "__main__":
    ejecutar_chat()