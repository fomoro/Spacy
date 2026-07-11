import spacy

# Cargar el modelo en español
nlp = spacy.load("es_core_news_sm")

# Procesar un texto
texto = nlp("María trabaja en Bogotá y compró dos libros ayer.")

print("TOKENS")
for token in texto:
    print(
        f"{token.text:<10} "
        f"Lema: {token.lemma_:<10} "
        f"Tipo: {token.pos_:<6} "
        f"Dependencia: {token.dep_}"
    )

print("\nENTIDADES")
for entidad in texto.ents:
    print(f"{entidad.text} -> {entidad.label_}")