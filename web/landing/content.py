"""Static content for the demo: the technique cards and the /analyze copy.

Pure data, no imports — the templates and the /analyze endpoint read from
here so the prose lives in one place instead of inline in the handlers.
"""

# Each scraping technique: what it does, where to practise it, and how to
# call it through the public /api endpoint (None when the API cannot host it).
TECHNIQUES = {
    "static": {
        "title": "1 · Static HTML",
        "subtitle": "requests + BeautifulSoup",
        "site": "books.toscrape.com",
        "api": "?method=html",
        "description": "The server sends the full HTML. We fetch it and parse it "
                       "with CSS selectors.",
    },
    "dynamic": {
        "title": "2 · Dynamic JS",
        "subtitle": "Playwright (real browser)",
        "site": "quotes.toscrape.com/js",
        "api": None,   # needs a real browser; not available on serverless
        "description": "JS fills the page. We launch a real browser and read the rendered DOM.",
    },
    "api": {
        "title": "3 · Intercepted API",
        "subtitle": "requests → JSON",
        "site": "quotes.toscrape.com/api",
        "api": "?method=json",
        "description": "Behind the JS there's an API with clean JSON. We hit it and skip the HTML.",
    },
    "crawl": {
        "title": "4 · Crawling at scale",
        "subtitle": "pagination + graph crawlers",
        "site": "quotes.toscrape.com",
        "description": "Hundreds of pages: walk a 'next' chain, or let BFS / Shark-Search / OPIC "
                       "order a whole site under a request budget.",
        "api": "?method=crawl&query=san+francisco",
    },
    "login": {
        "title": "5 · API with login",
        "subtitle": "session + CSRF token",
        "site": "quotes.toscrape.com/login",
        "api": None,   # needs credentials; local library only
        "description": "Data behind a login. We reuse the session cookie/token on every request.",
    },
    "markdown": {
        "title": "Extra · HTML → Markdown",
        "subtitle": "token savings for LLMs",
        "site": "quotes.toscrape.com",
        "api": "?method=markdown",
        "description": "Turns noisy HTML into clean Markdown: same info, a fraction of the tokens.",
    },
}


ANALYZE_I18N = {
    "en": {
        "bad_url": "Enter a URL that starts with http:// or https://",
        "download_err": "Could not download the page: {e}",
        "s1_t": "1 · Tried static HTML",
        "s1_d": "Fetched the page with requests (no browser). Status {status}, "
                "{elapsed}s, {chars} characters of visible text.",
        "s2_browser_t": "2 · Switched to a real browser",
        "s2_browser_d": "The HTML came back nearly empty, so I launched Chromium (Playwright) "
                        "and read the DOM already rendered by JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Wanted to use a browser",
        "s2_missing_d": "The HTML came back nearly empty (typical of an SPA), but Chromium isn't "
                        "installed. Run 'playwright install chromium' to enable this step.",
        "why_browser": "The static HTML had fewer than 200 characters of text: "
                       "a typical sign of a page that fills itself with JavaScript. "
                       "So I dropped the fast path and opened a real browser to see "
                       "the final content.",
        "why_missing": "The page seems to need JavaScript, but Chromium is "
                       "missing. I'm still showing what did come through via "
                       "static HTML.",
        "why_static": "The static HTML already had all the content, so no "
                      "browser was needed. It's the fastest, cheapest path: "
                      "a single HTTP request, no Chromium.",
        "no_title": "(no title)",
    },
    "es": {
        "bad_url": "Escribe una URL que empiece con http:// o https://",
        "download_err": "No se pudo descargar la página: {e}",
        "s1_t": "1 · Probé HTML estático",
        "s1_d": "Pedí la página con requests (sin navegador). Estado {status}, "
                "{elapsed}s, {chars} caracteres de texto visible.",
        "s2_browser_t": "2 · Cambié a un navegador real",
        "s2_browser_d": "El HTML volvió casi vacío, así que lancé Chromium (Playwright) "
                        "y leí el DOM ya renderizado por JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Quería usar un navegador",
        "s2_missing_d": "El HTML volvió casi vacío (típico de una SPA), pero Chromium no está "
                        "instalado. Corre 'playwright install chromium' para habilitar este paso.",
        "why_browser": "El HTML estático tenía menos de 200 caracteres de "
                       "texto: señal típica de una página que se rellena con "
                       "JavaScript. Así que dejé la vía rápida y abrí un navegador "
                       "real para ver el contenido final.",
        "why_missing": "La página parece necesitar JavaScript, pero falta "
                       "Chromium. Aun así muestro lo que sí llegó por HTML "
                       "estático.",
        "why_static": "El HTML estático ya tenía todo el contenido, así que "
                      "no hizo falta navegador. Es la vía más rápida y barata: "
                      "una sola petición HTTP, sin Chromium.",
        "no_title": "(sin título)",
    },
    "pt": {
        "bad_url": "Digite uma URL que comece com http:// ou https://",
        "download_err": "Não foi possível baixar a página: {e}",
        "s1_t": "1 · Tentei HTML estático",
        "s1_d": "Busquei a página com requests (sem navegador). Status {status}, "
                "{elapsed}s, {chars} caracteres de texto visível.",
        "s2_browser_t": "2 · Mudei para um navegador real",
        "s2_browser_d": "O HTML voltou quase vazio, então lancei o Chromium (Playwright) "
                        "e li o DOM já renderizado pelo JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Queria usar um navegador",
        "s2_missing_d": "O HTML voltou quase vazio (típico de uma SPA), mas o Chromium não está "
                        "instalado. Rode 'playwright install chromium' para habilitar este passo.",
        "why_browser": "O HTML estático tinha menos de 200 caracteres de "
                       "texto: sinal típico de uma página que se preenche com "
                       "JavaScript. Então abandonei o caminho rápido e abri um "
                       "navegador real para ver o conteúdo final.",
        "why_missing": "A página parece precisar de JavaScript, mas falta o "
                       "Chromium. Ainda assim mostro o que veio pelo HTML "
                       "estático.",
        "why_static": "O HTML estático já tinha todo o conteúdo, então não "
                      "foi preciso navegador. É o caminho mais rápido e barato: "
                      "uma única requisição HTTP, sem Chromium.",
        "no_title": "(sem título)",
    },
}
