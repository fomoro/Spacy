import json
import os

def cargar_json(nombre_archivo):
    """
    Carga un archivo JSON desde la carpeta datos/
    Entrada: Nombre del archivo
    Salida: Diccionario con los datos
    """
    # Obtener la ruta del directorio actual
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(directorio_actual, "..", "data", nombre_archivo)
    
    try:
        with open(ruta, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        print(f"⚠️ Error: No se encontró el archivo '{ruta}'")
        return {}
    except json.JSONDecodeError:
        print(f"⚠️ Error: El archivo '{ruta}' tiene formato JSON inválido")
        return {}

def guardar_json(nombre_archivo, datos):
    """
    Guarda datos en un archivo JSON
    Entrada: Nombre del archivo, datos a guardar
    Salida: True si se guardó correctamente, False si hubo error
    """
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(directorio_actual, "..", "datos", nombre_archivo)
    
    try:
        with open(ruta, 'w', encoding='utf-8') as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar '{ruta}': {e}")
        return False

def formatear_precio(precio):
    """
    Formatea un precio en pesos colombianos
    Entrada: Precio (int o str)
    Salida: String formateado con separadores de miles
    """
    if isinstance(precio, str):
        return precio
    return f"{precio:,.0f}".replace(",", ".")