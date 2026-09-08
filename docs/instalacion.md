# Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install bytecraw         # núcleo ligero: estático, APIs, crawlers
python3 -m pip install bytecraw[llm]    # + Markdown para LLMs
python3 -m pip install bytecraw[browser]  # + navegador para sitios con JS
python3 -m playwright install chromium  # solo si usas .browser()
```

---

[← Volver al índice](../README.md) · [Siguiente: Quickstart →](quickstart.md)
