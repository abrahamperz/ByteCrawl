# Quickstart

```python
from bytecrawl import Scraper

bot = Scraper(delay=0.5)
page = bot.static("https://books.toscrape.com")

print(page.status, page.method, page.elapsed)
print(page.css("h1"))
```

---

[← Volver al índice](../README.es.md) · [Siguiente: HTML estático →](01-html-estatico.md)
