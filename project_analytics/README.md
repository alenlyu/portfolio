# Project Analytics

A tiny self-hosted analytics server for multiple personal web projects.

## What it tracks

- Page views
- Unique visitors per project (browser-based anonymous client ID)
- Visits by day
- Referrer
- Path/page visited
- User-Agent
- Country when the hosting proxy provides `CF-IPCountry`
- IP is **not stored raw**; only a salted SHA-256 hash is stored

## Files

- `log.py` — Flask API + protected dashboard
- `static/tracker.js` — copy this file into each web project
- `requirements.txt` — Python dependency
- `.env.example` — environment variables
- `analytics.db` — created automatically on first run

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Set environment variables (see .env.example), then:
python log.py
```

Dashboard: `http://localhost:5000/dashboard`

Default login is `admin` / `change-me-now` only if you did not set environment variables. Change it before deployment.

## Add a project

In the HTML of each website, before `</head>`:

```html
<script>
  window.PROJECT_ANALYTICS_ENDPOINT = "https://YOUR-ANALYTICS-DOMAIN/log";
  window.PROJECT_ANALYTICS_PROJECT = "simona";
</script>
<script src="https://YOUR-ANALYTICS-DOMAIN/static/tracker.js"></script>
```

For a new project, change only the project name:

```html
<script>
  window.PROJECT_ANALYTICS_PROJECT = "my-new-project";
</script>
<script src="https://YOUR-ANALYTICS-DOMAIN/static/tracker.js"></script>
```

Keep the endpoint line if you are using a separate HTML project and have not changed it globally.

## Important distinction

`Views` = number of page loads received.

`Unique visitors` = approximate distinct browsers, based on an anonymous ID in `localStorage`. Clearing storage, using private browsing, or changing browsers/devices can create another visitor ID.

## Telegram bot

A Telegram bot is not a normal web page, so this tracker cannot directly count every person who opens the bot chat. For Telegram, log a bot-side event such as `/start` using the Telegram Bot API. The same `/log` endpoint can be extended for that later.

## Deployment

Deploy this folder to any Python host that supports Flask and persistent disk/storage. Make sure the SQLite file is on persistent storage; otherwise visits can disappear after a redeploy.

Set:

- `ANALYTICS_USER`
- `ANALYTICS_PASSWORD`
- `ANALYTICS_HASH_SECRET`
- optionally `ANALYTICS_PROJECTS`

Then use the public HTTPS URL as `PROJECT_ANALYTICS_ENDPOINT`.

## Security notes

The `/dashboard` and `/api/*` endpoints use HTTP Basic Authentication. The `/log` endpoint is intentionally public because browser JavaScript cannot safely keep a secret. For a public personal portfolio this is usually sufficient together with rate limiting at the hosting/proxy layer.
