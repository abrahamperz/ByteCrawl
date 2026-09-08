# Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install bytecrawl         # núcleo ligero: estático, APIs, crawlers
python3 -m pip install bytecrawl[llm]    # + Markdown para LLMs
python3 -m pip install bytecrawl[browser]  # + navegador para sitios con JS
python3 -m playwright install chromium  # solo si usas .browser()
```

---

[← Volver al índice](../README.md) · [Siguiente: Quickstart →](quickstart.md)
