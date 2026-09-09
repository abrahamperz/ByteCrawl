# Estrategia mental

Ante un sitio nuevo, prueba en este orden:

1. **¿Hay una API por detrás?** → datos JSON limpios, lo mejor.
   [API oculta](03-api-oculta.md)
2. **¿El HTML es estático?** → rápido y sencillo.
   [HTML estático](01-html-estatico.md)
3. **¿Solo se ve con JavaScript?** → saca el navegador.
   [JS dinámico](02-js-dinamico.md)
4. **¿Son muchas páginas con paginación conocida?** → crawling con paginación.
   [Crawling con paginación](04-crawling-paginacion.md)
5. **¿Está detrás de login?** → sesión autenticada.
   [Login con sesión](05-login-sesion.md)
6. **¿Explorar un sitio entero por tema o importancia?** → crawling de grafos.
   [Crawling de grafos](06-crawling-grafos.md)

`bot.fetch(url, strategy="auto")` aplica esto solo: prueba estático y, si la
página viene casi vacía (típico de SPAs), reintenta con navegador.

Ojo con la palabra "estrategia", que aquí significa dos cosas distintas. La de
`fetch(strategy=...)` es **cómo se descarga una página** (`static`, `browser`,
`api`, `auto`). La de `focused_crawl(strategy=...)` es **en qué orden se recorre
un sitio** (`shark`, `opic`, `bfs`) y solo aplica al paso 6.

Si quien lee esto es un agente de IA, hay una versión de este mismo árbol de
decisión escrita para agentes, con llamadas listas para copiar:

```
Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

Y si lo lees tú: [SKILL.md](https://bytecrawl.vercel.app/agent-onboarding/SKILL.md).

---

[← Volver al índice](../README.es.md) · [Siguiente: Nota ética →](nota-etica.md)
