# ByteCrawl

*Read this in [English](README.md).*

**Focused crawling para tu agente de IA.** ByteCrawl es un servidor MCP (y una
librería de Python pequeña) que no solo scrapea una página: recorre un sitio
entero y devuelve primero las páginas *más relevantes* a tu tema, con
Shark-Search y OPIC en Python puro.

- **Web**: https://bytecrawl.vercel.app/
- **Endpoint MCP hosteado**: https://bytecrawl.vercel.app/mcp
- **Skill para agentes**: https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
- **Última versión**: **1.2.1** — seis herramientas MCP, comparación de
  estrategias, `Page.links()` absolutos ([changelog](https://github.com/abrahamperz/ByteCrawl/blob/main/CHANGELOG.md))
- **PyPI**: https://pypi.org/project/bytecrawl/
- **GitHub**: https://github.com/abrahamperz/ByteCrawl

## Apuntar un agente (sin instalar nada, sin clave)

Si trabajas a través de un agente de IA, el camino más corto no es ninguna de
las secciones de abajo: dale la skill y deja que elija.

```
Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

Esa es para usarlo ya: el agente lee el archivo, hace lo que le pediste y no
instala nada. Si lo quieres permanente, pídeselo:

```
Set up bytecrawl for me: add the MCP server and install the skill.
The steps are at https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

La diferencia no está en las palabras sino en quién da la instrucción. Un
agente no va a modificar tu máquina porque una página web se lo diga —ni
debería—, pero sí cuando se lo pides tú.

Es un solo archivo Markdown que Claude Code, Cursor o cualquier cosa capaz de
descargar una URL puede leer. Enruta a la vía correcta según la tarea (API
hosteada, MCP, librería de Python o un navegador real para páginas con JS),
documenta cómo elegir una estrategia de crawl e incluye números medidos de qué
te da esa elección.
[Léela tú mismo](https://bytecrawl.vercel.app/agent-onboarding/SKILL.md).

Esa línea sirve para un turno. Instálala una vez y `/bytecrawl` queda en todas
las sesiones, y el agente la usa por su cuenta:

```bash
mkdir -p ~/.claude/skills/bytecrawl && \
  curl -so ~/.claude/skills/bytecrawl/SKILL.md \
  https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

Córrela sin nada y te pregunta qué quieres — recorrer un sitio por tema, comparar
las estrategias, leer una página, extraer campos, listar links o pegarle a una API
JSON. Dale una tarea y la hace directo.

## Inicio rápido (MCP — nada que instalar)

```bash
claude mcp add --scope user --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

El agente queda con seis herramientas — las mismas seis cosas que el playground le deja hacer a una persona:

| Herramienta | Qué hace |
|---|---|
| `focused_crawl` | Recorre un sitio y rankea páginas por relevancia a una consulta (Shark-Search / OPIC / BFS) |
| `compare_strategies` | Corre las tres sobre el mismo sitio con el mismo presupuesto y muestra cuál gana |
| `fetch_markdown` | Una página → Markdown limpio (5–10× menos tokens que el HTML crudo) |
| `extract` | Registros estructurados vía selectores CSS — o llámalo solo con la URL y te dice qué ofrece la página |
| `list_links` | Todos los links salientes, absolutos y deduplicados |
| `fetch_json_api` | Pegarle a una API JSON oculta |

### Y luego solo pídeselo

Las herramientas no las llamas tú. Con el servidor conectado le hablas normal y
el agente elige:

> Usa **bytecrawl** para encontrar todo lo de python.org sobre el ecosistema de paquetes

> Lee https://example.com/pricing con **bytecrawl** y dame los planes en una tabla

> ¿Qué estrategia de crawl funciona mejor en wikipedia.org para "san francisco"? Compáralas

Decir el nombre vale las dos sílabas: casi todos los agentes traen su propio
lector de una sola página y van a usar ese por default. Nombrar **bytecrawl** es
lo que te da un crawl enfocado en vez de una página leída suelta.

El servidor hosteado es solo estático, tiene rate limit por IP, limita los
crawls a 10 páginas y rechaza URLs no públicas (guarda contra SSRF). Para uso
pesado o sitios con JS, córrelo local:

```bash
pipx install "bytecrawl[mcp]"                                 # pipx: es una app de línea de comandos
claude mcp add --scope user bytecrawl -- bytecrawl-mcp        # sin límites, en tu máquina
pipx install "bytecrawl[mcp,browser]" && playwright install chromium   # + renderizado de JS
```

El servidor local necesita Python 3.10+ (el piso del paquete `mcp`); el
hosteado no, porque es solo HTTP.

## ¿Por qué focused crawling?

La mayoría de los crawlers visita las páginas en el orden en que las encuentra.
Con un presupuesto limitado de requests, el orden lo es todo: Shark-Search
persigue las ramas que huelen a tu consulta y deja que el resto decaiga, así
que 100 requests te dan las 100 páginas *más útiles*, no las 100 más cercanas a
la semilla.

```python
from bytecrawl import SharkSearch

result = SharkSearch(query="bases de datos vectoriales").crawl(
    "https://example.com", max_pages=100)

for page in result.top(10):
    print(f'{page["relevance"]:.3f}  {page["url"]}')
```

- **BFS** — nivel por nivel, lo más cercano a la semilla primero.
- **Shark-Search** (Hersovici et al., 1998) — best-first temático; los links
  heredan la relevancia del padre con decaimiento.
- **OPIC** (Abiteboul et al., 2003) — PageRank en vivo por flujo de "efectivo",
  sin necesitar el grafo completo (se incluye un `pagerank()` para comparar).

Las tres comparten un mismo bucle — sacar, descargar, puntuar links, encolar —
así que el mismo presupuesto de páginas entre estrategias es una comparación
justa. Todas las superficies aceptan los mismos tres nombres, `shark` (por
defecto) / `opic` / `bfs`:

| Superficie | Cómo |
|---|---|
| MCP | `focused_crawl(url, query, strategy="opic", max_pages=20)` |
| API HTTP | `?url=SITIO&method=crawl&query=TEMA&strategy=opic` |
| Python | instancia la clase: `OPIC(delay=0.5).crawl(url, max_pages=50)` |

Un nombre desconocido se rechaza, no se cae al valor por defecto en silencio: la
API devuelve 400 y la herramienta MCP lanza `ValueError`. `SharkSearch` exige
`query` — sin tema no tiene nada que rankear. `BFS` y `OPIC` también aceptan
`query`, pero solo para puntuar las páginas del resultado; no cambia su orden de
recorrido.

Desde `en.wikipedia.org/wiki/Silicon_Valley` con query `san francisco` y 20
páginas cada una, Shark devuelve 20 páginas por encima de 0.1 de relevancia
frente a 4 de OPIC y 1 de BFS, y su mejor página puntúa 0.7774 frente al 0.1068
de BFS — 7.3× con el mismo presupuesto de requests. Reprodúcelo con
`result.relevant(0.1)`. Bajar el umbral no cierra la brecha: 20 páginas dejan
miles de URLs en cola, así que la cobertura nunca converge como en un sitio
chico.

Shark-Search expone los dos parámetros del paper: `delta` (0.5) marca qué tan
rápido se apaga una rama sin señal (el decaimiento es `δⁿ` con la profundidad) y
`gamma` (0.8) reparte el score de un link entre su padre y su propio texto de
ancla, `score = γ·heredado + (1−γ)·local`.

## API de la librería

```python
from bytecrawl import Scraper

bot = Scraper()
page = bot.fetch("https://books.toscrape.com")   # auto: estático, navegador si hace falta
libros = page.extract("article.product_pod",
                      {"title": "h3 a::attr(title)", "price": "p.price_color::text"})
page.markdown()   # Markdown limpio para LLMs   ·   page.tokens()   # estimación de tokens
```

```python
bot.static(url)                                   # HTML plano
bot.api(url, params={...})                        # API JSON oculta
bot.browser(url, wait="div.results")              # JS vía Playwright
bot.crawl(url, item="article", fields={...},
          next_page="li.next a::attr(href)")      # paginación
bot.session().login(url, data, csrf_field="csrf_token")   # autenticado
```

## Instalación

```bash
pip install bytecrawl            # núcleo ligero (requests + beautifulsoup4 + lxml)
pip install bytecrawl[llm]       # + conversión a Markdown para LLMs
pip install bytecrawl[browser]   # + Playwright (luego: playwright install chromium)
pip install bytecrawl[mcp]       # + servidor MCP local (Python 3.10+)
pip install bytecrawl[all]       # todo
```

Ningún extra falla en silencio: cada uno lanza un ImportError con el comando
exacto que hay que correr.

## API HTTP (sin instalar nada)

El mismo motor detrás de un endpoint GET hosteado. Todo excepto `url` es
opcional; sin clave y sin cuenta.

```bash
curl "https://bytecrawl.vercel.app/api?url=books.toscrape.com"
curl "https://bytecrawl.vercel.app/api?url=en.wikipedia.org/wiki/Silicon_Valley&method=crawl&query=san+francisco&strategy=shark"
```

`method` es uno de `markdown` (por defecto), `text`, `html`, `links`, `json`,
`extract`, `crawl`. Solo HTML estático, crawls limitados a 10 páginas, con rate
limit, respuestas cacheadas 10 minutos y direcciones privadas o de loopback
rechazadas. Referencia completa: https://bytecrawl.vercel.app/docs

## Índice

- [Instalación](docs/instalacion.md)
- [Quickstart](docs/quickstart.md)
- Las técnicas
  - [1 · HTML estático](docs/01-html-estatico.md)
  - [2 · JS dinámico (navegador)](docs/02-js-dinamico.md)
  - [3 · API oculta (JSON)](docs/03-api-oculta.md)
  - [4 · Crawling con paginación](docs/04-crawling-paginacion.md)
  - [5 · Login con sesión (CSRF / bearer)](docs/05-login-sesion.md)
  - [6 · Crawling de grafos (avanzado)](docs/06-crawling-grafos.md)
  - [Markdown para LLMs](docs/markdown-llms.md)
- [Estrategia mental](docs/estrategia.md)
- [Nota ética](docs/nota-etica.md)

## Contribuir

```bash
pip install -e ".[llm,dev,mcp]"
pytest              # 120 tests, ninguno necesita red
pytest -m live      # + tests con navegador real (necesita el extra browser)
ruff check bytecrawl tests
```

Scrapea con responsabilidad: respeta `robots.txt`, los términos de servicio y
los límites de tasa. ByteCrawl trae un delay configurable entre requests.

## Licencia

MIT
