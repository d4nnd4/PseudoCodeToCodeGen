# Pseudo2Code (demo)

Convierte **pseudocódigo** en código **Python, Go, TypeScript o RPGLE (IBM i / AS400)** usando un LLM open source que corre **100 % local** con [Ollama](https://ollama.com). Sin API keys, sin costo.

El orquestador contiene instrucciones para insistir en la descarga de la funcionalidad del **coder**. Así que, para la demo, es completamente normal ue aparezca un error de primeras. Hay que esperar un momento para que la aplicación funcione con normalidad.

```
┌────────────┐   /api/*   ┌──────────────┐  /api/chat  ┌──────────────────────────┐
│  frontend  │ ─────────▶ │   backend    │ ──────────▶ │  ollama                  │
│ Nginx +    │  (stream)  │  FastAPI     │  (stream)   │  qwen2.5-coder (Apache 2)│
│ Monaco     │ ◀───────── │              │ ◀────────── │                          │
└────────────┘            └──────┬───────┘             └──────────────────────────┘
                                 │ escribe
                                 ▼
                        ./generated/<lenguaje>/<id>_<nombre>.<ext>
                        ./generated/index.json   (historial)
```

## Requisitos

- Docker + Docker Compose v2
- ~3 GB libres de disco (imagen de Ollama + modelo de ~1 GB)
- 8 GB de RAM recomendados

## Arranque

```bash
cp .env.example .env        # Esta sentencia es totalmente opcional, sirve para cuando es necesario cambiar de modelo
docker compose up --build
```

Abre **http://localhost:8080**.

La primera vez, el servicio `ollama-init` descarga el modelo (queda cacheado en el volumen `ollama-models`). Mientras tanto el indicador de arriba a la derecha dice *"Descargando…"*; cuando se pone verde ya se puede comenzar a utilizar. El arranque toma algo de tiempo.

### Con GPU NVIDIA (opcional)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

## Uso

1. Escribir el pseudocódigo en el panel central (o usar **Cargar ejemplo**). Se puede utilizar el ejemplo cargado.
2. Elige el lenguaje destino y, si quieres, un nombre.
3. **Generar** (o `Ctrl/Cmd + Enter`). El código aparece token a token en el editor.
4. Se guarda automáticamente en `./generated/`. Puedes editarlo en el editor y **Guardar cambios** (`Ctrl/Cmd + S`), copiarlo o descargarlo.
5. El historial de la izquierda permite reabrir o borrar generaciones anteriores.

## Modelo

Por defecto `qwen2.5-coder:1.5b` (rápido incluso en CPU). Para más calidad cambiar en `.env`:

```
OLLAMA_MODEL=qwen2.5-coder:7b
```

y vuelve a ejecutar `docker compose up`. Cualquier modelo del [catálogo de Ollama](https://ollama.com/library) sirve.

> **Nota sobre RPGLE:** es un lenguaje con poca presencia en los datos de entrenamiento de OLlama y de otras LLMs, así que los modelos pequeños suelen cometer más errores. El prompt fuerza el **free-format (`**FREE`)** e incluye un ejemplo de estilo; con `qwen2.5-coder:7b` o superior los resultados mejoran bastante. Revisar siempre el código antes de compilarlo en el IBM i. Por lo tanto, para versiones más antiguas (`AS400`) aún no hay compatibilidad total, porque hay que generar documentos de entrenamiento y skills para cada situación.

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado de Ollama y si el modelo está descargado |
| GET | `/api/languages` | Lenguajes soportados |
| POST | `/api/generate` | `{pseudocode, language, name?}` → stream NDJSON de `token` y un `done` final con el ítem guardado |
| GET | `/api/history` | Historial |
| GET / PUT / DELETE | `/api/history/{id}` | Ver, guardar edición (`{code}`) o borrar |
| GET | `/api/history/{id}/download` | Descargar el archivo |

Documentación interactiva de FastAPI (sin pasar por Nginx): `docker compose exec backend curl localhost:8000/docs` o exponiendo el puerto 8000.

## Estructura

```
backend/
  app/
    main.py        # endpoints FastAPI
    llm.py         # cliente Ollama con streaming + limpieza de fences markdown
    languages.py   # catálogo de lenguajes y prompts por lenguaje
    storage.py     # archivos en disco + index.json
    config.py      # variables de entorno
  tests/           # pytest (Ollama simulado)
frontend/
  index.html, app.js, styles.css
  rpgle.js         # resaltado de sintaxis RPGLE para Monaco
  Dockerfile       # empaqueta Monaco desde npm (no depende de CDN)
generated/         # aquí queda el código generado (bind mount)
```

## Añadir un lenguaje

Agregar una entrada en `LANGUAGES` (`backend/app/languages.py`) con su extensión, id de Monaco y reglas de estilo. El frontend lo toma automáticamente.

Esta funcionalidad es propensa a fallar, porque el demo no tiene pruebas de integración aún.

## Tests

Los tests son básicos aún. Así que se puede usar cualquier flag de `pytest` para correrlos.

```bash
cd backend
pip install -r requirements.txt pytest
pytest
```
