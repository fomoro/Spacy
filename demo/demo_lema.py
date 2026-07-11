import spacy

# Cargar el modelo en español
nlp = spacy.load("es_core_news_sm")

# Procesar el texto
texto = nlp("Los perros corren rápido por el parque.")

# Imprimir el lema de cada palabra
for token in texto:
    print(f"Palabra: {token.text} -> Lema: {token.lemma_}")
