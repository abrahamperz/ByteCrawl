# 6 · Crawling de grafos (avanzado)

La web es un grafo: páginas = nodos, links = aristas. Un crawler decide en qué
**orden** visitar las URLs con un presupuesto limitado de requests. ByteCrawl trae
tres estrategias con el mismo loop y distinto algoritmo de orden:

| Estrategia | Idea | Optimiza |
|---|---|---|
| `BFS` | recorre por niveles desde la semilla | cobertura cercana |
| `SharkSearch` | best-first temático: los links heredan score de padres relevantes con decaimiento δ (Hersovici et al., 1998) | relevancia a un tema |
| `OPIC` | cada página tiene "cash" que reparte a sus links al ser visitada; es PageRank calculado en vivo (Abiteboul et al., 2003) | importancia estructural |

## Cómo funciona el loop común

Las tres estrategias comparten exactamente el mismo ciclo; lo único que cambia
es **cómo puntúan los links** que van descubriendo:

1. Saca de la *frontier* (una priority queue) la URL con mayor score.
2. Descarga la página y mide su relevancia al query (similitud coseno TF).
3. Extrae sus links, los puntúa según la estrategia y los mete a la frontier.
4. Repite hasta agotar el presupuesto (`max_pages`).

Como el código del loop es idéntico, comparar estrategias es justo: misma
máquina, mismos requests, distinta función de orden.

## BFS — anchura clásica

El score de cada link es `-(profundidad + 1)`: cuanto más cerca de la semilla,
antes se visita. Es el recorrido por niveles de toda la vida: primero todos los
links de la portada, luego los links de esos links, etc.

- **Fortaleza**: cobertura uniforme alrededor de la semilla; nunca se pierde en
  una rama profunda.
- **Debilidad**: es ciego al tema. Si buscas "machine learning", gasta requests
  en /contacto y /login igual que en /blog/ml.

## Shark-Search — perseguir el tema

Cada link recibe un score que mezcla dos señales:

```
score(link) = γ · heredado + (1 − γ) · señal_local
```

- **Heredado**: si el padre fue relevante al query, los hijos heredan
  `δ · relevancia(padre)`; si no, heredan `δ · heredado(padre)`. Como δ < 1,
  una rama sin señal se apaga geométricamente (δ, δ², δ³...) — el crawler
  abandona solo los callejones sin salida.
- **Señal local**: similitud coseno entre el query y el *texto del anchor* +
  las palabras de la URL (`/tag/love/` ya dice mucho antes de descargarla).

Con γ = 0.8 y δ = 0.5 (los defaults), domina la herencia pero el anchor puede
"rescatar" un link prometedor de un padre mediocre. El resultado: el crawler
se comporta como un tiburón que huele sangre — en cuanto encuentra una página
relevante, se queda explorando esa zona del grafo.

- **Fortaleza**: con el mismo presupuesto encuentra 2-3× más páginas relevantes
  que BFS (pruébalo en el demo).
- **Debilidad**: necesita un query; sin tema que perseguir, degenera.

## OPIC — importancia sin tema

No usa query: estima qué páginas son **estructuralmente importantes** (muy
enlazadas), como PageRank, pero **en vivo** mientras crawlea:

1. La semilla nace con cash = 1.0.
2. Al visitar una página: su cash se suma a su *historial* (importancia
   acumulada), se pone a 0 y se reparte **equitativamente entre sus links**.
3. Siempre se visita la URL con más cash pendiente.

La intuición: si muchas páginas apuntan a `/about`, esa URL acumula cash de
muchos padres y sube en la cola. El total de cash del sistema se conserva
(invariante del algoritmo); las páginas sin links de salida (sumideros)
devuelven su cash a las URLs conocidas no visitadas — el "nodo virtual" del
paper.

- **Fortaleza**: encuentra los hubs del sitio sin necesitar el grafo completo
  ni un query.
- **Debilidad**: importancia ≠ relevancia; el hub puede ser /login.

## PageRank offline — el experimento

`pagerank(result.graph)` calcula PageRank clásico (iteración de potencias,
damping 0.85) sobre el grafo que el crawl dejó registrado. Comparar ese
ranking offline contra el historial de cash de OPIC sobre el mismo grafo es
justamente el experimento del paper: OPIC aproxima online lo que PageRank
calcula con el grafo completo.

## Uso

```python
from bytecrawl import BFS, SharkSearch, OPIC, pagerank

result = SharkSearch(query="machine learning").crawl(
    "https://example.com", max_pages=100)

result.pages           # visitadas en orden, con relevancia coseno de cada una
result.relevant(0.2)   # solo las que superan el umbral
result.stats           # requests, relevantes encontradas, relevancia promedio

pagerank(result.graph) # PageRank offline sobre el grafo crawleado
```

La relevancia se mide con similitud coseno TF (implementada en la librería, sin
dependencias). Pruébalas en vivo y compáralas en
[bytecrawl.vercel.app/methods](https://bytecrawl.vercel.app/methods#advanced).

## Elegir una estrategia desde fuera de Python

No hace falta escribir código para cambiar de estrategia. Las tres superficies
aceptan los mismos tres nombres — `shark` (por defecto), `opic`, `bfs`:

| Superficie | Cómo |
|---|---|
| API HTTP | `?url=SITIO&method=crawl&query=TEMA&strategy=opic` |
| MCP | `focused_crawl(url, query, strategy="opic", max_pages=20)` |
| Python | instanciar la clase: `OPIC(delay=0.5).crawl(url, max_pages=50)` |

Un nombre desconocido no se cae al valor por defecto en silencio: la API
devuelve 400 y la herramienta MCP lanza `ValueError` listando los válidos.

`SharkSearch` exige `query` como argumento obligatorio — sin tema no tiene nada
que rankear. `BFS` y `OPIC` también lo aceptan, pero ahí solo sirve para
puntuar las páginas del resultado; no cambia su orden de recorrido.

## Ajustar Shark-Search

Los dos parámetros del paper están expuestos:

```python
SharkSearch(query="machine learning", delta=0.5, gamma=0.8)
```

- `delta` (0.5) — qué tan rápido se apaga una rama sin señal. El decaimiento es
  `δⁿ` con la profundidad, así que 0.3 abandona antes las ramas malas y 0.7 les
  da más margen.
- `gamma` (0.8) — cuánto del score de un link viene del padre frente a su propio
  texto de ancla: `score = γ·heredado + (1−γ)·local`. Bájalo cuando el texto de
  ancla del sitio sea descriptivo y confíes más en él que en la estructura.

Los valores por defecto son razonables; cámbialos solo si un crawl se está yendo
del tema (baja `delta`) o si ignora links obviamente relevantes (baja `gamma`).

## Qué te da la elección, medido

Desde `en.wikipedia.org/wiki/Silicon_Valley`, query `san francisco`, 20 páginas
y 20 requests cada una:

| Estrategia | Páginas sobre 0.1 de relevancia | Mejor página | Media del top 5 |
|---|---|---|---|
| `shark` | 20 | 0.7774 | 0.6523 |
| `opic` | 4 | 0.2799 | 0.1715 |
| `bfs` | 1 | 0.1068 | 0.0733 |

Reprodúcelo con `result.relevant(0.1)` en cada una. Las tres gastaron los mismos
20 requests; lo único que cambió es a dónde fueron. La mejor página de Shark
puntúa 7.3× la de BFS, y su top 5 promedia 8.9×.

Bajar el umbral no rescata a BFS acá: las tres terminan con miles de URLs sin
visitar en la cola — 3.8k Shark, 8.6k BFS, 16.8k OPIC — así que la cobertura
nunca converge. Ese es el caso para el que vale la pena diseñar: el orden
importa justamente cuando el presupuesto es chico frente al sitio.

## Referencias

- Hersovici et al. (1998), *The shark-search algorithm — an application:
  tailored Web site mapping*.
- Abiteboul, Preda & Cobena (2003), *Adaptive On-Line Page Importance
  Computation*.
- Page, Brin, Motwani & Winograd (1999), *The PageRank Citation Ranking*.

---

[← Volver al índice](../README.es.md) · [Siguiente: Markdown para LLMs →](markdown-llms.md)
