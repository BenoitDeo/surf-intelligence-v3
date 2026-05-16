# SurfCheck

SurfCheck ranks Peniche-area surf spots from Windguru forecasts fetched through
Apify's `fortuitous_pirate/windguru-forecast-agent`.

## Cheapest setup that works while driving

ChatGPT custom MCP apps are currently web-only, and ChatGPT Voice does not run
Custom GPT actions. For true hands-free use from an iPhone, use an iOS Shortcut:

1. Deploy this app to Render.
2. Copy your deployed `/voice` URL.
3. Create an iPhone Shortcut named `Surf Check`.
4. Add `Get Contents of URL` with:
   `https://your-render-service.onrender.com/voice?token=YOUR_TOKEN`
5. Add `Speak Text`, using the result from the URL step.
6. While driving, say: `Hey Siri, Surf Check`.

That will speak a sentence like:

```text
Best call right now: Supertubos (8.0/10). Wind NE at 11 km/h, swell 1.6 m at 13s.
```

### Hosting choice

Render Free is the cheapest option: `$0/month`, but it spins down after 15
minutes idle, so the first request can take about a minute. Render Starter is
the simplest reliable option for driving: `$7/month`, no cold start.

Railway Hobby is currently `$5/month`, but it has a required subscription.
Fly.io can be cheap, but it is less beginner-friendly and has usage-based
billing. For this project, use Render unless you already prefer another host.

## Use from ChatGPT on web

Deploy this project as a public web service, then connect it as a Developer mode
app in ChatGPT web.

The MCP endpoint will be:

```text
https://your-deployed-domain.example/mcp
```

In ChatGPT:

1. Open Settings > Apps.
2. Enable Developer mode if needed.
3. Create app.
4. Use the deployed `/mcp` URL as the MCP Server URL.
5. In a chat, use the tools menu or prompt ChatGPT to use SurfCheck, and ask:
   `Where should I surf near Peniche right now?`

The MCP tool exposed to ChatGPT is `best_surf_spot`.

One quick deployment path is Render:

1. Push this repo to GitHub.
2. Create a new Render Blueprint or Web Service from the repo.
3. Use `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python mcp_server.py`
4. Add `APIFY_TOKEN` in Render environment variables.
5. Use `https://your-render-service.onrender.com/mcp` in ChatGPT web.

This first version is intentionally simple and does not implement OAuth on the
SurfCheck MCP server itself. Keep the URL private, or add MCP auth before
sharing it broadly.

## Apify MCP setup

In ChatGPT Developer mode, create the Apify app with:

- Name: `Apify`
- MCP Server URL:
  `https://mcp.apify.com/?tools=actors,docs,fortuitous_pirate/windguru-forecast-agent`
- Authentication: OAuth

Then authorize the app with Apify and select it from `+ > Developer mode` in a
conversation.

For local API runs, set:

```sh
APIFY_TOKEN=your_apify_token
```

For Render, set `APIFY_TOKEN` as an environment variable in the Render dashboard.
Set `SURFCHECK_ACCESS_TOKEN` too. This protects the Siri Shortcut endpoints.

## Run

Local unified server:

```sh
uvicorn server:app --reload
```

Open `GET /surf` for JSON, `GET /voice` for spoken text, or `/mcp` for MCP.

Forecast a specific time with the `at` query parameter:

```sh
curl "http://localhost:8000/voice?at=tomorrow%209am"
curl "http://localhost:8000/surf?at=2026-05-17T09:00:00%2B01:00"
```

In ChatGPT web MCP, ask: `What will be the best surf spot tomorrow at 9am?`

## Windguru spot IDs

The configured numeric Windguru spot IDs are in `config/spots.py`.
Key verified IDs:

- Praia Areia Branca: `58060`
- Peniche: `1528`
- Baleal: `501140`
- Peniche & Baleal: `48951`
- Supertubos: `55936`
- Lagido: `39832`
- Cantinho da Baia: `500477`

Some hyper-local breaks only exist as user-created Windguru entries, so the app
uses the closest exact-name match returned by Windguru search.
