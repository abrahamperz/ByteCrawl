# Markdown para LLMs

Convierte el HTML ruidoso en Markdown limpio: misma info, fracción de tokens.

```python
md = page.markdown()                 # only the main content
md_full = page.markdown(main_only=False)  # the whole page
print(page.tokens(), "->", page.tokens(of=md))
```

---

[← Volver al índice](../README.es.md) · [Siguiente: Estrategia mental →](estrategia.md)
