# Guía rápida de librerías Python

## 1. Instalar las librerías

Abrir PowerShell o CMD y ejecutar:

```powershell
py -m pip install --default-timeout=100 numpy pandas openpyxl xlsxwriter fastapi flask uvicorn requests sqlalchemy mysql-connector-python pymysql spacy python-dotenv pydantic httpx loguru playwright
```

## 2. Instalar y probar spaCy

Instalar los modelos en español:

```powershell
py -m spacy download es_core_news_sm
py -m spacy download es_core_news_md
```

Probar el modelo pequeño:

```powershell
py -c "import spacy; nlp=spacy.load('es_core_news_sm'); doc=nlp('Hola, quiero crear un asistente para WhatsApp.'); print([(t.text,t.pos_) for t in doc]); print('spaCy SM: OK')"
```

Probar el modelo mediano:

```powershell
py -c "import spacy; nlp=spacy.load('es_core_news_md'); doc=nlp('El cliente consulta sus facturas pendientes.'); print([(t.text,t.pos_) for t in doc]); print('spaCy MD: OK')"
```

## 3. Instalar y probar Playwright

Instalar Chromium:

```powershell
py -m playwright install chromium
```

Probar Playwright:

```powershell
py -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); print('Playwright OK:',b.version); b.close(); p.stop()"
```

## 4. Crear un proyecto

### Usar las librerías directamente

```powershell
mkdir mi_proyecto
cd mi_proyecto
notepad prueba.py
```

Contenido de `prueba.py`:

```python
import spacy

nlp = spacy.load("es_core_news_md")
doc = nlp("El cliente consulta sus facturas pendientes.")

print([(token.text, token.pos_) for token in doc])
```

Ejecutar:

```powershell
py prueba.py
```

### Usar un entorno virtual

```powershell
mkdir mi_proyecto
cd mi_proyecto
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install spacy
python -m spacy download es_core_news_md
python prueba.py
```

## Validación general

```powershell
py -c "import fastapi, flask, uvicorn, requests, sqlalchemy, pymysql, mysql.connector, pandas, numpy, openpyxl, xlsxwriter, spacy, httpx, loguru; print('Librerías principales: OK')"
```
