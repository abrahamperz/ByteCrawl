# 2 · JS dinámico (navegador)

Cuando el contenido lo rellena JavaScript, abre un Chromium real (Playwright)
y lee el DOM ya pintado. Puedes esperar a un selector o hacer scroll para lazy load.

```python
page = bot.browser("https://quotes.toscrape.com/js", scroll=True)
print(page.css_all("span.text"))
```

---

[← Volver al índice](../README.es.md) · [Siguiente: API oculta →](03-api-oculta.md)
