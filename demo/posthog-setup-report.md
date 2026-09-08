<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog into the ByteCrawl Flask demo app. A `Posthog` client instance is initialized at startup using `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` environment variables. A session-based anonymous `distinct_id` is generated per visitor (stored in the Flask session) so individual user journeys can be tracked across requests without requiring authentication. The client is shut down gracefully on process exit via `atexit`. Three server-side events are captured across the two highest-value routes.

| Event | Description | File |
|---|---|---|
| `scrape_technique_run` | Fired when a user runs one of the six scraping technique demos from `/methods`. Properties: `technique`, `technique_title`, `success`, `duration_seconds`, `record_count`. | `app.py` |
| `url_analyzed` | Fired when a user submits a URL to the auto-strategy analyzer on `/try`. Properties: `method_used`, `used_browser`, `chromium_missing`, `steps_count`, `has_markdown`, `token_reduction_ratio`. | `app.py` |
| `scrape_data_retrieved` | Fired when a user views previously cached scraping results without re-running a script (`/data/<clave>`). Properties: `technique`, `has_data`, `record_count`. | `app.py` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) — Dashboard](https://us.posthog.com/project/465031/dashboard/1697111)
- [Scrape technique runs over time](https://us.posthog.com/project/465031/insights/46AfM21Q) — Daily trend of technique runs
- [URLs analyzed over time](https://us.posthog.com/project/465031/insights/W2hZdV4R) — Daily trend of playground usage
- [Most popular scraping techniques](https://us.posthog.com/project/465031/insights/hB2RJZXS) — Bar chart breakdown by technique name
- [URL analysis method: browser vs static](https://us.posthog.com/project/465031/insights/zksJ6Zri) — Pie chart of which strategy ByteCrawl chose
- [Funnel: URL analyzed → Scrape run](https://us.posthog.com/project/465031/insights/ogrzW0UP) — Conversion from playground to running a real technique

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-flask/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
