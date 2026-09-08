# ByteCraw

*Read this in [English](README.md).*

Una sola API de Python para scrapear cualquier sitio: HTML estático, JS dinámico,
APIs ocultas, login con sesión, crawling y Markdown listo para LLMs. Incluye
crawlers de grafos (BFS, Shark-Search, OPIC) para **focused crawling**: visitar
solo las páginas relevantes a tu tema con un presupuesto limitado de requests.

- **Demo**: https://byte-craw.vercel.app/
- **PyPI**: https://pypi.org/project/bytecraw/
- **GitHub**: https://github.com/abrahamperz/ByteCraw

## Instalación

```bash
pip install bytecraw            # núcleo ligero (requests + beautifulsoup4 + lxml)
pip install bytecraw[llm]       # + conversión a Markdown para LLMs
pip install bytecraw[browser]   # + Playwright para sitios con JS
pip install bytecraw[all]       # todo
```

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

## Licencia

MIT
