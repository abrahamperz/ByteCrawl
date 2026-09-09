# 1 · HTML estático

Para sitios donde el servidor ya manda el HTML completo. Una petición HTTP,
parseo con selectores CSS (soporta `::text` y `::attr(nombre)`).

```python
page = bot.static("https://books.toscrape.com")

books = page.extract("article.product_pod", {
    "title": "h3 a::attr(title)",
    "price": "p.price_color::text",
})
```

---

[← Volver al índice](../README.es.md) · [Siguiente: JS dinámico →](02-js-dinamico.md)
