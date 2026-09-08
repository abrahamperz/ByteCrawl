// Cliente i18n: traduce elementos [data-i18n], [data-i18n-html] y [data-i18n-ph].
// Idioma persistido en localStorage. Sin dependencias, funciona en serverless.
(function () {
  const DICT = {
    en: {
      nav_docs: "Docs", nav_methods: "Methods", nav_try: "Try",

      hero_humans: "For humans", hero_agents: "For agents",
      hero_h1: 'Universal <span class="grad">scraping layer</span>',
      hero_sub: "A unified Python SDK for scraping any website—static HTML, dynamic JS, hidden APIs, and LLM-ready Markdown output, all behind one type-safe API.",
      cta_get_started: "Get started", cta_try_live: "Try it live", copy: "copy", copied: "copied ✓",
      ns_label: "Now, in your code:", ns_docs: "For more, see the Docs →",
      adv_eyebrow: "Advanced methods",
      adv_h2: "Graph crawling: BFS vs Shark-Search vs OPIC",
      adv_desc: "The web is a graph. A crawler decides which URL to visit next with a limited request budget. BFS sweeps by levels, Shark-Search chases a topic (best-first with inherited scores), OPIC computes page importance online like a live PageRank. Same loop, different ordering — run all three on a site and compare.",
      adv_query_ph: "topic query",
      adv_run: "Run comparison", adv_running: "Crawling with", adv_done: "Done — higher avg relevance with the same budget wins",
      adv_pages: "pages", adv_time: "time", adv_avgrel: "avg relevance", adv_relevant: "relevant",
      adv_pr: "PageRank (offline) on the crawled graph:",
      adv_what_bfs: "Sweeps level by level from the seed. The fair baseline.",
      adv_what_shark: "Priority queue by topic score: links inherit from relevant parents, bad branches decay.",
      adv_what_opic: "Each page holds cash and splits it among its links when visited. Online PageRank.",
      card_site_label: "practice site:",
      adv_exp_bfs_1: "Classic level-order sweep: every link gets the score",
      adv_exp_bfs_2: "so the closest pages to the seed are visited first. Uniform coverage, but blind to the topic: it spends requests on /login just like on /blog.",
      adv_exp_shark_1: "Topical best-first. Each link blends what its parent passed down with its own anchor + URL words:",
      adv_exp_shark_2: "Children of a relevant parent inherit δ·relevance; barren branches decay as δⁿ and die off on their own. The crawler swarms the relevant region of the graph.",
      adv_exp_opic_1: "Online importance, no query needed. The seed starts with cash = 1.0; on each visit the page banks its cash into its history and splits it evenly among its links:",
      adv_exp_opic_2: "Heavily linked pages accumulate cash from many parents and jump the queue — a live PageRank, computed while crawling.",
      stat1: "Fewer LLM tokens", stat2: "From any page", stat3: "Unified API", stat4: "Config to start",
      sec1_eyebrow: "The strategy-agnostic toolkit",
      sec1_h2: "One API. Every scraping strategy.",
      sec1_lead: "From a single static page to a JS-heavy SPA to a hidden JSON API—ByteCrawl picks the right tool, or you choose explicitly.",
      feat1_t: "Auto-strategy", feat1_p: "Tries static HTML first, falls back to a real browser when a page is JS-rendered. No guessing.",
      feat2_t: "API-first", feat2_p: "Hit the JSON API behind a site and skip HTML entirely. Up to 2.5× faster than a headless browser.",
      feat3_t: "LLM-ready", feat3_p: "Convert any page to clean Markdown with one call. Strips noise, slashes token cost for agents.",
      sec2_eyebrow: "Powered by the best", sec2_h2: "Scale with confidence",
      sec2_lead: "ByteCrawl stands on a battle-tested ecosystem—each strategy backed by a proven engine.",
      eco1_d: "Robust HTML parsing and CSS selectors for static pages.",
      eco2_d: "Real Chromium for JS-heavy SPAs and interaction.",
      eco3_d: "Industrial crawling: queues, concurrency, retries.",
      eco4_d: "Main-content extraction to token-light Markdown.",
      foot_h2: "Build with ByteCrawl today",
      foot_lead: "Start by exploring the docs, or open the live dashboard to run every strategy.",
      cta_open_methods: "Open methods", cta_read_docs: "Read the docs",

      m_eyebrow: "The methods", m_h1: "Every scraping strategy, explained",
      m_sub: 'What each technique does, the site it targets, and when to reach for it. Want to run them live? Open the <a href="/try" style="color:var(--text);font-weight:600;text-decoration:underline">playground</a>.',
      m_strat_label: "The order to try, from cleanest to most expensive",
      m_s_api: '<span class="n">3</span> Is there an API?',
      m_s_static: '<span class="n">1</span> Static HTML?',
      m_s_js: '<span class="n">2</span> JS only?',
      m_s_many: '<span class="n">4</span> Thousands of pages?',
      m_s_login: '<span class="n">5</span> Behind login?',
      m_s_download: '<span class="n">6</span> Download the output',
      card_static_t: "1 · Static HTML", card_static_d: "The server sends the full HTML. We fetch it and parse it with CSS selectors.",
      card_dynamic_t: "2 · Dynamic JS", card_dynamic_d: "JS fills the page. We launch a real browser and read the rendered DOM.",
      card_api_t: "3 · Intercepted API", card_api_d: "Behind the JS there's an API with clean JSON. We hit it and skip the HTML.",
      card_scrapy_t: "4 · Scrapy at scale", card_scrapy_d: "Industrial framework: handles URL queue, parallelism, retries and export.",
      card_login_t: "5 · API with login", card_login_d: "Data behind a login. We reuse the session cookie/token on every request.",
      card_markdown_t: "Extra · HTML → Markdown", card_markdown_d: "Turns noisy HTML into clean Markdown: same info, a fraction of the tokens.",

      try_eyebrow: "Interactive playground", try_h1: "Try it with any URL",
      try_sub: "Paste a page and ByteCrawl picks the strategy, scrapes it, and explains what it did and why.",
      azr_title: "Analyze any URL",
      azr_sub: "Paste a page: ByteCrawl picks the strategy (static or browser) and explains what it did and why.",
      azr_hint: "Change the URL and try yours.",
      analyze_btn: "Analyze",
      adv_disc: "discovered (request budget)", adv_download: "Download results (.json)",
      adv_lbl_query: "Topic to chase",
      badge_deep: "Graph analyzer",
      badge_tokens: "Markdown saves {pct}% of LLM tokens",
      st_enter_url: "✗ Enter a URL", st_analyzing: "Analyzing the page...", st_strategy: "Strategy used:",
      badge_title: "title", badge_links: "links",
      md_ready: "Extracted Markdown · ready for an LLM", md_copy: "Copy .md", md_download: "↓ Download .md", why_q: "Why did it do that?",

      d_grp_start: "Getting started", d_grp_api: "API reference", d_grp_guides: "Guides",
      d_install: "Installation", d_quickstart: "Quickstart",
      d_selectors: "Selector syntax", d_strategy: "Choosing a strategy",
      d_h1: "ByteCrawl docs",
      d_lead: "A unified Python toolkit for scraping any website—static HTML, dynamic JS, hidden APIs, authenticated sessions, and LLM-ready Markdown, all behind one API.",
      d_quickstart_p: 'Create a <code class="inline">Scraper</code>, fetch a page, extract typed records.',
      d_scraper_p: 'The entry point. Pick a strategy explicitly, or let <code class="inline">fetch()</code> decide.',
      d_crawl_ex: "crawl example",
      d_page_p: "What every fetch returns. Holds the HTML (or JSON), timing, and extraction helpers.",
      d_session_p: "An authenticated session. Cookies persist across requests; chainable.",
      d_selectors_p: "Selectors are plain CSS plus two pseudo-suffixes, and a list marker on field names.",
      d_strategy_p: "Go from cheapest to heaviest. The right order saves time and avoids bans:",
      d_li_api: '<b>API?</b> Check DevTools → Network for a JSON endpoint. Cleanest and fastest → <code class="inline">.api()</code>',
      d_li_static: '<b>Static HTML?</b> If "View source" already shows the data → <code class="inline">.static()</code>',
      d_li_js: '<b>JS-only?</b> Empty source but data on screen → <code class="inline">.browser()</code>',
      d_li_many: '<b>Many pages?</b> → <code class="inline">.crawl()</code> (or the Scrapy method in the playground)',
      d_li_login: '<b>Behind login?</b> → <code class="inline">.session().login()</code>',
      d_try_live: 'Try it live in the <a href="/methods" style="color:var(--accent);font-weight:600">Methods playground</a>.',
    },
    es: {
      nav_docs: "Docs", nav_methods: "Métodos", nav_try: "Probar",

      hero_humans: "Para humanos", hero_agents: "Para agentes",
      hero_h1: 'Capa universal de <span class="grad">scraping</span>',
      hero_sub: "Un SDK de Python unificado para scrapear cualquier sitio: HTML estático, JS dinámico, APIs ocultas y salida en Markdown lista para LLMs, todo tras una sola API.",
      cta_get_started: "Empieza", cta_try_live: "Pruébalo en vivo", copy: "copiar", copied: "copiado ✓",
      ns_label: "Ahora, en tu código:", ns_docs: "Para más, mira los Docs →",
      adv_eyebrow: "Métodos avanzados",
      adv_h2: "Crawling de grafos: BFS vs Shark-Search vs OPIC",
      adv_desc: "La web es un grafo. Un crawler decide qué URL visitar después con un presupuesto limitado de requests. BFS barre por niveles, Shark-Search persigue un tema (best-first con scores heredados), OPIC calcula la importancia de cada página en vivo, como un PageRank online. Mismo loop, distinto orden: corre las tres sobre un sitio y compara.",
      adv_query_ph: "query temático",
      adv_run: "Correr comparación", adv_running: "Crawleando con", adv_done: "Listo — gana la mayor relevancia promedio con el mismo presupuesto",
      adv_pages: "páginas", adv_time: "tiempo", adv_avgrel: "relevancia prom.", adv_relevant: "relevantes",
      adv_pr: "PageRank (offline) sobre el grafo crawleado:",
      adv_what_bfs: "Barre nivel por nivel desde la semilla. La línea base justa.",
      adv_what_shark: "Priority queue por score temático: los links heredan de padres relevantes, las ramas malas decaen.",
      adv_what_opic: "Cada página tiene cash y lo reparte entre sus links al ser visitada. PageRank online.",
      card_site_label: "sitio de práctica:",
      adv_exp_bfs_1: "Barrido clásico por niveles: cada link recibe el score",
      adv_exp_bfs_2: "así que las páginas más cercanas a la semilla se visitan primero. Cobertura uniforme, pero ciego al tema: gasta requests en /login igual que en /blog.",
      adv_exp_shark_1: "Best-first temático. Cada link mezcla lo que hereda de su padre con su propio anchor + palabras de la URL:",
      adv_exp_shark_2: "Los hijos de un padre relevante heredan δ·relevancia; las ramas sin señal decaen como δⁿ y se apagan solas. El crawler se concentra en la zona relevante del grafo.",
      adv_exp_opic_1: "Importancia online, sin query. La semilla nace con cash = 1.0; al visitar una página, su cash se suma a su historial y se reparte equitativamente entre sus links:",
      adv_exp_opic_2: "Las páginas muy enlazadas acumulan cash de muchos padres y suben en la cola: un PageRank en vivo, calculado mientras se crawlea.",
      stat1: "Menos tokens de LLM", stat2: "Desde cualquier página", stat3: "API unificada", stat4: "Config para empezar",
      sec1_eyebrow: "El toolkit agnóstico de estrategia",
      sec1_h2: "Una API. Todas las estrategias de scraping.",
      sec1_lead: "De una sola página estática a una SPA cargada de JS o una API JSON oculta: ByteCrawl elige la herramienta correcta, o la eliges tú.",
      feat1_t: "Estrategia automática", feat1_p: "Prueba HTML estático primero y cambia a un navegador real cuando la página usa JS. Sin adivinar.",
      feat2_t: "API primero", feat2_p: "Pega a la API JSON detrás de un sitio y sáltate el HTML por completo. Hasta 2.5× más rápido que un navegador headless.",
      feat3_t: "Listo para LLM", feat3_p: "Convierte cualquier página a Markdown limpio con una llamada. Elimina el ruido y reduce el costo de tokens para agentes.",
      sec2_eyebrow: "Impulsado por lo mejor", sec2_h2: "Escala con confianza",
      sec2_lead: "ByteCrawl se apoya en un ecosistema probado en batalla: cada estrategia respaldada por un motor consolidado.",
      eco1_d: "Parseo de HTML robusto y selectores CSS para páginas estáticas.",
      eco2_d: "Chromium real para SPAs cargadas de JS e interacción.",
      eco3_d: "Crawling industrial: colas, concurrencia, reintentos.",
      eco4_d: "Extracción del contenido principal a Markdown ligero en tokens.",
      foot_h2: "Construye con ByteCrawl hoy",
      foot_lead: "Empieza explorando la documentación, o abre el panel en vivo para correr cada estrategia.",
      cta_open_methods: "Ver métodos", cta_read_docs: "Lee la documentación",

      m_eyebrow: "Los métodos", m_h1: "Cada estrategia de scraping, explicada",
      m_sub: 'Qué hace cada técnica, el sitio al que apunta y cuándo usarla. ¿Quieres correrlas en vivo? Abre el <a href="/try" style="color:var(--text);font-weight:600;text-decoration:underline">playground</a>.',
      m_strat_label: "El orden a probar, de lo más limpio a lo más costoso",
      m_s_api: '<span class="n">3</span> ¿Hay API?',
      m_s_static: '<span class="n">1</span> ¿HTML estático?',
      m_s_js: '<span class="n">2</span> ¿Solo con JS?',
      m_s_many: '<span class="n">4</span> ¿Miles de páginas?',
      m_s_login: '<span class="n">5</span> ¿Tras login?',
      m_s_download: '<span class="n">6</span> Descargar el output',
      card_static_t: "1 · HTML estático", card_static_d: "El servidor manda el HTML completo. Lo pedimos y parseamos con selectores CSS.",
      card_dynamic_t: "2 · JS dinámico", card_dynamic_d: "El JS rellena la página. Lanzamos un navegador real y leemos el DOM ya pintado.",
      card_api_t: "3 · API interceptada", card_api_d: "Detrás del JS hay una API con JSON limpio. La copiamos y nos saltamos el HTML.",
      card_scrapy_t: "4 · Scrapy a escala", card_scrapy_d: "Framework industrial: maneja cola de URLs, paralelismo, reintentos y export.",
      card_login_t: "5 · API con login", card_login_d: "Datos detrás de login. Reutilizamos la cookie/token de sesión en cada petición.",
      card_markdown_t: "Extra · HTML → Markdown", card_markdown_d: "Convierte el HTML ruidoso a Markdown limpio: misma info, fracción de tokens.",

      try_eyebrow: "Playground interactivo", try_h1: "Pruébalo con cualquier URL",
      try_sub: "Pega una página y ByteCrawl elige la estrategia, la scrapea y te explica qué hizo y por qué.",
      azr_title: "Analiza cualquier URL",
      azr_sub: "Pega una página: ByteCrawl elige la estrategia (estático o navegador) y te explica qué hizo y por qué.",
      azr_hint: "Cambia la URL y prueba la tuya.",
      analyze_btn: "Analizar",
      adv_disc: "descubiertas (presupuesto de requests)", adv_download: "Descargar resultados (.json)",
      adv_lbl_query: "Tema a perseguir",
      badge_deep: "Analizador de grafo",
      badge_tokens: "El Markdown ahorra {pct}% de tokens de LLM",
      st_enter_url: "✗ Escribe una URL", st_analyzing: "Analizando la página...", st_strategy: "Estrategia usada:",
      badge_title: "título", badge_links: "enlaces",
      md_ready: "Markdown extraído · listo para un LLM", md_copy: "Copiar .md", md_download: "↓ Descargar .md", why_q: "¿Por qué hizo eso?",

      d_grp_start: "Para empezar", d_grp_api: "Referencia de API", d_grp_guides: "Guías",
      d_install: "Instalación", d_quickstart: "Inicio rápido",
      d_selectors: "Sintaxis de selectores", d_strategy: "Elegir una estrategia",
      d_h1: "Docs de ByteCrawl",
      d_lead: "Un toolkit de Python unificado para scrapear cualquier sitio: HTML estático, JS dinámico, APIs ocultas, sesiones autenticadas y Markdown listo para LLMs, todo tras una sola API.",
      d_quickstart_p: 'Crea un <code class="inline">Scraper</code>, pide una página y extrae registros tipados.',
      d_scraper_p: 'El punto de entrada. Elige una estrategia explícita, o deja que <code class="inline">fetch()</code> decida.',
      d_crawl_ex: "ejemplo de crawl",
      d_page_p: "Lo que devuelve cada fetch. Contiene el HTML (o JSON), los tiempos y los helpers de extracción.",
      d_session_p: "Una sesión autenticada. Las cookies persisten entre peticiones; encadenable.",
      d_selectors_p: "Los selectores son CSS plano más dos pseudo-sufijos, y un marcador de lista en los nombres de campo.",
      d_strategy_p: "Ve de lo más barato a lo más pesado. El orden correcto ahorra tiempo y evita bloqueos:",
      d_li_api: '<b>¿API?</b> Revisa DevTools → Network buscando un endpoint JSON. Lo más limpio y rápido → <code class="inline">.api()</code>',
      d_li_static: '<b>¿HTML estático?</b> Si "Ver código fuente" ya muestra los datos → <code class="inline">.static()</code>',
      d_li_js: '<b>¿Solo con JS?</b> Código fuente vacío pero datos en pantalla → <code class="inline">.browser()</code>',
      d_li_many: '<b>¿Muchas páginas?</b> → <code class="inline">.crawl()</code> (o el método Scrapy en el playground)',
      d_li_login: '<b>¿Tras login?</b> → <code class="inline">.session().login()</code>',
      d_try_live: 'Pruébalo en vivo en el <a href="/methods" style="color:var(--accent);font-weight:600">playground de Métodos</a>.',
    },
    pt: {
      nav_docs: "Docs", nav_methods: "Métodos", nav_try: "Testar",

      hero_humans: "Para humanos", hero_agents: "Para agentes",
      hero_h1: 'Camada universal de <span class="grad">scraping</span>',
      hero_sub: "Um SDK de Python unificado para fazer scraping de qualquer site: HTML estático, JS dinâmico, APIs ocultas e saída em Markdown pronta para LLMs, tudo por trás de uma única API.",
      cta_get_started: "Começar", cta_try_live: "Teste ao vivo", copy: "copiar", copied: "copiado ✓",
      ns_label: "Agora, no seu código:", ns_docs: "Para mais, veja os Docs →",
      adv_eyebrow: "Métodos avançados",
      adv_h2: "Crawling de grafos: BFS vs Shark-Search vs OPIC",
      adv_desc: "A web é um grafo. Um crawler decide qual URL visitar em seguida com um orçamento limitado de requests. BFS varre por níveis, Shark-Search persegue um tema (best-first com scores herdados), OPIC calcula a importância de cada página ao vivo, como um PageRank online. Mesmo loop, ordem diferente: rode as três em um site e compare.",
      adv_query_ph: "query temática",
      adv_run: "Rodar comparação", adv_running: "Crawleando com", adv_done: "Pronto — vence a maior relevância média com o mesmo orçamento",
      adv_pages: "páginas", adv_time: "tempo", adv_avgrel: "relevância média", adv_relevant: "relevantes",
      adv_pr: "PageRank (offline) sobre o grafo rastreado:",
      adv_what_bfs: "Varre nível por nível a partir da semente. A linha de base justa.",
      adv_what_shark: "Priority queue por score temático: os links herdam de pais relevantes, ramos ruins decaem.",
      adv_what_opic: "Cada página tem cash e o distribui entre seus links ao ser visitada. PageRank online.",
      card_site_label: "site de prática:",
      adv_exp_bfs_1: "Varredura clássica por níveis: cada link recebe o score",
      adv_exp_bfs_2: "então as páginas mais próximas da semente são visitadas primeiro. Cobertura uniforme, mas cega ao tema: gasta requests em /login igual que em /blog.",
      adv_exp_shark_1: "Best-first temático. Cada link mistura o que herda do pai com seu próprio anchor + palavras da URL:",
      adv_exp_shark_2: "Os filhos de um pai relevante herdam δ·relevância; ramos sem sinal decaem como δⁿ e se apagam sozinhos. O crawler se concentra na região relevante do grafo.",
      adv_exp_opic_1: "Importância online, sem query. A semente nasce com cash = 1.0; ao visitar uma página, seu cash é somado ao histórico e dividido igualmente entre seus links:",
      adv_exp_opic_2: "Páginas muito linkadas acumulam cash de muitos pais e sobem na fila: um PageRank ao vivo, calculado durante o crawl.",
      stat1: "Menos tokens de LLM", stat2: "De qualquer página", stat3: "API unificada", stat4: "Config para começar",
      sec1_eyebrow: "O toolkit agnóstico de estratégia",
      sec1_h2: "Uma API. Todas as estratégias de scraping.",
      sec1_lead: "De uma única página estática a uma SPA cheia de JS ou uma API JSON oculta: o ByteCrawl escolhe a ferramenta certa, ou você escolhe.",
      feat1_t: "Estratégia automática", feat1_p: "Tenta HTML estático primeiro e muda para um navegador real quando a página usa JS. Sem adivinhação.",
      feat2_t: "API primeiro", feat2_p: "Acesse a API JSON por trás de um site e pule o HTML por completo. Até 2,5× mais rápido que um navegador headless.",
      feat3_t: "Pronto para LLM", feat3_p: "Converta qualquer página em Markdown limpo com uma chamada. Remove o ruído e reduz o custo de tokens para agentes.",
      sec2_eyebrow: "Movido pelos melhores", sec2_h2: "Escale com confiança",
      sec2_lead: "O ByteCrawl se apoia em um ecossistema testado em batalha: cada estratégia sustentada por um motor consolidado.",
      eco1_d: "Parsing de HTML robusto e seletores CSS para páginas estáticas.",
      eco2_d: "Chromium real para SPAs cheias de JS e interação.",
      eco3_d: "Crawling industrial: filas, concorrência, retentativas.",
      eco4_d: "Extração do conteúdo principal para Markdown leve em tokens.",
      foot_h2: "Construa com o ByteCrawl hoje",
      foot_lead: "Comece explorando a documentação, ou abra o painel ao vivo para rodar cada estratégia.",
      cta_open_methods: "Ver métodos", cta_read_docs: "Leia a documentação",

      m_eyebrow: "Os métodos", m_h1: "Cada estratégia de scraping, explicada",
      m_sub: 'O que cada técnica faz, o site que ela mira e quando usá-la. Quer rodar ao vivo? Abra o <a href="/try" style="color:var(--text);font-weight:600;text-decoration:underline">playground</a>.',
      m_strat_label: "A ordem para tentar, do mais limpo ao mais caro",
      m_s_api: '<span class="n">3</span> Tem API?',
      m_s_static: '<span class="n">1</span> HTML estático?',
      m_s_js: '<span class="n">2</span> Só com JS?',
      m_s_many: '<span class="n">4</span> Milhares de páginas?',
      m_s_login: '<span class="n">5</span> Atrás de login?',
      m_s_download: '<span class="n">6</span> Baixar o output',
      card_static_t: "1 · HTML estático", card_static_d: "O servidor envia o HTML completo. Pedimos e parseamos com seletores CSS.",
      card_dynamic_t: "2 · JS dinâmico", card_dynamic_d: "O JS preenche a página. Lançamos um navegador real e lemos o DOM renderizado.",
      card_api_t: "3 · API interceptada", card_api_d: "Por trás do JS há uma API com JSON limpo. Acessamos e pulamos o HTML.",
      card_scrapy_t: "4 · Scrapy em escala", card_scrapy_d: "Framework industrial: gerencia fila de URLs, paralelismo, retentativas e export.",
      card_login_t: "5 · API com login", card_login_d: "Dados atrás de login. Reutilizamos o cookie/token de sessão em cada requisição.",
      card_markdown_t: "Extra · HTML → Markdown", card_markdown_d: "Transforma HTML ruidoso em Markdown limpo: mesma info, uma fração dos tokens.",

      try_eyebrow: "Playground interativo", try_h1: "Teste com qualquer URL",
      try_sub: "Cole uma página e o ByteCrawl escolhe a estratégia, faz o scraping e explica o que fez e por quê.",
      azr_title: "Analise qualquer URL",
      azr_sub: "Cole uma página: o ByteCrawl escolhe a estratégia (estático ou navegador) e explica o que fez e por quê.",
      azr_hint: "Troque a URL e teste a sua.",
      analyze_btn: "Analisar",
      adv_disc: "descobertas (orçamento de requests)", adv_download: "Baixar resultados (.json)",
      adv_lbl_query: "Tema a perseguir",
      badge_deep: "Analisador de grafo",
      badge_tokens: "O Markdown economiza {pct}% dos tokens de LLM",
      st_enter_url: "✗ Digite uma URL", st_analyzing: "Analisando a página...", st_strategy: "Estratégia usada:",
      badge_title: "título", badge_links: "links",
      md_ready: "Markdown extraído · pronto para um LLM", md_copy: "Copiar .md", md_download: "↓ Baixar .md", why_q: "Por que fez isso?",

      d_grp_start: "Começando", d_grp_api: "Referência da API", d_grp_guides: "Guias",
      d_install: "Instalação", d_quickstart: "Início rápido",
      d_selectors: "Sintaxe de seletores", d_strategy: "Escolher uma estratégia",
      d_h1: "Docs do ByteCrawl",
      d_lead: "Um toolkit de Python unificado para fazer scraping de qualquer site: HTML estático, JS dinâmico, APIs ocultas, sessões autenticadas e Markdown pronto para LLMs, tudo por trás de uma única API.",
      d_quickstart_p: 'Crie um <code class="inline">Scraper</code>, busque uma página e extraia registros tipados.',
      d_scraper_p: 'O ponto de entrada. Escolha uma estratégia explícita, ou deixe o <code class="inline">fetch()</code> decidir.',
      d_crawl_ex: "exemplo de crawl",
      d_page_p: "O que cada fetch retorna. Contém o HTML (ou JSON), os tempos e os helpers de extração.",
      d_session_p: "Uma sessão autenticada. Os cookies persistem entre requisições; encadeável.",
      d_selectors_p: "Os seletores são CSS puro mais dois pseudo-sufixos, e um marcador de lista nos nomes dos campos.",
      d_strategy_p: "Vá do mais barato ao mais pesado. A ordem certa economiza tempo e evita bloqueios:",
      d_li_api: '<b>API?</b> Verifique DevTools → Network por um endpoint JSON. O mais limpo e rápido → <code class="inline">.api()</code>',
      d_li_static: '<b>HTML estático?</b> Se "Ver código-fonte" já mostra os dados → <code class="inline">.static()</code>',
      d_li_js: '<b>Só com JS?</b> Código-fonte vazio mas dados na tela → <code class="inline">.browser()</code>',
      d_li_many: '<b>Muitas páginas?</b> → <code class="inline">.crawl()</code> (ou o método Scrapy no playground)',
      d_li_login: '<b>Atrás de login?</b> → <code class="inline">.session().login()</code>',
      d_try_live: 'Teste ao vivo no <a href="/methods" style="color:var(--accent);font-weight:600">playground de Métodos</a>.',
    },
  };

  const LANGS = ["en", "es", "pt"];
  function getLang() {
    const saved = localStorage.getItem("bc_lang");
    if (saved && LANGS.includes(saved)) return saved;
    const nav = (navigator.language || "en").slice(0, 2);
    return LANGS.includes(nav) ? nav : "en";
  }

  let current = getLang();

  // t(key): one-off translation for strings generated in JS.
  window.t = function (key) {
    return (DICT[current] && DICT[current][key]) || (DICT.en[key] != null ? DICT.en[key] : key);
  };
  window.currentLang = function () { return current; };

  function apply(lang) {
    current = lang;
    const d = DICT[lang] || DICT.en;
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const k = el.getAttribute("data-i18n");
      if (d[k] != null) el.textContent = d[k];
    });
    document.querySelectorAll("[data-i18n-html]").forEach(el => {
      const k = el.getAttribute("data-i18n-html");
      if (d[k] != null) el.innerHTML = d[k];
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(el => {
      const k = el.getAttribute("data-i18n-ph");
      if (d[k] != null) el.setAttribute("placeholder", d[k]);
    });
    document.querySelectorAll(".lang-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-lang") === lang);
    });
    document.dispatchEvent(new CustomEvent("bc:lang", { detail: lang }));
  }

  window.setLang = function (lang) {
    if (!LANGS.includes(lang)) return;
    localStorage.setItem("bc_lang", lang);
    apply(lang);
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".lang-btn").forEach(b => {
      b.addEventListener("click", () => window.setLang(b.getAttribute("data-lang")));
    });
    apply(current);
  });
})();
