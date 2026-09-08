# 4 · Crawling con paginación

Recorre múltiples páginas siguiendo el enlace "siguiente" y junta todos los registros.

```python
items = bot.crawl(
    "https://quotes.toscrape.com",
    item="div.quote",
    fields={"quote": "span.text::text", "tags[]": "a.tag::text"},
    next_page="li.next a::attr(href)",
)
```

---

[← Volver al índice](../README.md) · [Siguiente: Login con sesión →](05-login-sesion.md)
