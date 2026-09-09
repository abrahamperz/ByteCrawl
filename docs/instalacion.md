# Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install bytecrawl         # núcleo ligero: estático, APIs, crawlers
python3 -m pip install bytecrawl[llm]    # + Markdown para LLMs
python3 -m pip install bytecrawl[browser]  # + navegador para sitios con JS
python3 -m playwright install chromium  # solo si usas .browser()
python3 -m pip install bytecrawl[mcp]    # + servidor MCP local (Python 3.10+)
python3 -m pip install bytecrawl[all]    # todo lo anterior
```

El núcleo son tres paquetes (`requests`, `beautifulsoup4`, `lxml`). Ningún extra
falla en silencio: si te falta uno, el ImportError te dice el comando exacto.

## Sin instalar nada

Dos caminos que no tocan tu máquina:

```bash
# API HTTP hosteada
curl "https://bytecrawl.vercel.app/api?url=books.toscrape.com"

# MCP hosteado, para agentes
claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

Y si le estás pasando esto a un agente de IA, dale la skill en vez de la
documentación — elige el camino solo:

```
Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

Puedes [leer la skill tú mismo](https://bytecrawl.vercel.app/agent-onboarding/SKILL.md)
si quieres ver a qué camino te va a mandar.

---

[← Volver al índice](../README.es.md) · [Siguiente: Quickstart →](quickstart.md)
