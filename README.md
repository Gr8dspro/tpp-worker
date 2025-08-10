# TPP Worker (Batch generator for Best Alternatives pages)

This repo runs two scheduled jobs:
- **discover.py** (daily): finds discontinued/OOS products from public sitemaps, selects 3–6 alternatives, and posts pages to your WordPress endpoint.
- **refresh.py** (every 12h): rechecks existing items' price/availability/ratings and updates reasons.

## Quick start

1) Create a GitHub repo and upload these files.
2) In the repo, set **Settings → Secrets and variables → Actions → New repository secret**:
   - `TPP_ENDPOINT` — your WP endpoint (from WP Admin → Settings → TPP Alternatives), e.g. `https://toppickpilot.com/wp-json/tpp/v1/ingest`
   - `TPP_SECRET` — your ingest secret (from the same settings page).
3) Edit `merchants.yml` to include **public product sitemaps** (respect robots.txt).
4) Enable Actions. The workflow runs on schedule, or run it manually via **Run workflow**.

> This worker respects robots.txt and uses conditional requests (ETag/Last-Modified). Keep heavy crawling off WordPress.

## Dev: run locally

```bash
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r worker/requirements.txt
export TPP_ENDPOINT="https://toppickpilot.com/wp-json/tpp/v1/ingest"
export TPP_SECRET="YOUR_SECRET"
python worker/discover.py
python worker/refresh.py
```

## What gets sent to WP
Payload example:
```json
{
  "items": [{
    "original_name": "Acme Widget 3000",
    "original_url": "https://example.com/acme-widget-3000",
    "status": "discontinued",
    "slug": "acme-widget-3000",
    "explanation": "Closest current models with similar capacity and price.",
    "alternatives": [
      {"name":"Acme Widget 4000","url":"https://merchant.com/...","price":"$129","merchant":"Merchant A","reason":"Newer model"}
    ]
  }]
}
```
