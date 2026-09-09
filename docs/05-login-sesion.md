# 5 · Login con sesión (CSRF / bearer)

Reutiliza la cookie o token de sesión en cada petición para acceder a datos
detrás de un login.

```python
s = bot.session().login(url, data=creds, csrf_field="csrf_token")
home = s.fetch("https://quotes.toscrape.com")

# or with a token:
s = bot.session().bearer("eyJhbGci...")
```

---

[← Volver al índice](../README.es.md) · [Siguiente: Crawling de grafos →](06-crawling-grafos.md)
