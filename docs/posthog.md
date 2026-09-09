# PostHog analytics (landing app)

Server-side product analytics for the landing/demo app (`web/landing/`). This
documents what is actually instrumented; it started life as a wizard report and
has been kept in step with the code since.

## How it is wired

All analytics lives in `web/landing/analytics.py`:

- One process-wide `Posthog` client, created at import from `POSTHOG_PROJECT_TOKEN`
  and `POSTHOG_HOST` (falls back to no-op when the key is empty).
- A per-visitor `distinct_id`: a UUID stored in the Flask `session`, so a
  journey can be followed across requests without any login.
- `track(event, properties)` — the only entry point routes use. It resolves the
  distinct id and calls `posthog_client.capture(...)` **inside a try/except**, so
  a broken or unconfigured analytics backend can never fail a request.
- `register(app)` wires a `flush()` on teardown and `atexit` registers
  `posthog_client.shutdown()` for a clean exit.

Routes stay thin: the handler in `web/landing/routes.py` calls into
`web/landing/services.py`, which returns `(payload, status, props)`. The handler
fires `analytics.track(...)` only when `props is not None` (i.e. on success).

## Events

Two server-side events, both on the JSON endpoints — the highest-signal actions.

| Event | Fired from | Built in | Properties |
|---|---|---|---|
| `url_analyzed` | `POST /analyze` (`routes.py`) | `services.analyze_url` | `method_used`, `used_browser`, `chromium_missing`, `steps_count`, `has_markdown`, `token_reduction_ratio` |
| `crawl_strategy_run` | `POST /crawl` (`routes.py`) | `services.run_crawl` | `strategy`, plus everything in the crawl's `result.stats` (pages fetched, etc.) |

`url_analyzed` captures what the auto-strategy analyzer did on a submitted URL
(which fetch method it picked, whether it fell back to the browser, how many
steps it explained, and the HTML→Markdown token reduction). `crawl_strategy_run`
captures one focused-crawl run — the frontend compares strategies by calling
`/crawl` three times in parallel, so each strategy is its own event.

> The earlier version of this app also fired `scrape_technique_run` and
> `scrape_data_retrieved` from the old monolithic `app.py`. Those routes were
> removed in the refactor to the `web/landing/` package; only the two events
> above exist now. Any PostHog insight built on the retired events no longer
> receives data.

## Dashboard

The PostHog project (id `465031`) has a starter dashboard and insights created
with the integration:

- [Analytics basics — Dashboard](https://us.posthog.com/project/465031/dashboard/1697111)
- [URLs analyzed over time](https://us.posthog.com/project/465031/insights/W2hZdV4R)
- [URL analysis method: browser vs static](https://us.posthog.com/project/465031/insights/zksJ6Zri)

Insights tied to the retired `scrape_technique_run` event (technique-popularity
bar chart, the playground→scrape funnel) will read empty until they are pointed
at the current events.
