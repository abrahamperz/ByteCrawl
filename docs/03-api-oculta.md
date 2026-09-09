# 3 · API oculta (JSON)

Detrás del JS casi siempre hay una API con JSON limpio. La pides directo y te
saltas el HTML por completo: lo más rápido y estable.

```python
data = bot.api("https://quotes.toscrape.com/api/quotes", params={"page": 1})
print(data.json())
```

---

[← Volver al índice](../README.es.md) · [Siguiente: Crawling con paginación →](04-crawling-paginacion.md)
