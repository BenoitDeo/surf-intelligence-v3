# SurfCheck

SurfCheck ranks Peniche-area surf spots from forecasts fetched directly from
Windguru's web forecast API.

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
4. Add `SURFCHECK_ACCESS_TOKEN` in Render environment variables.
5. Use `https://your-render-service.onrender.com/mcp` in ChatGPT web.

This first version is intentionally simple and does not implement OAuth on the
SurfCheck MCP server itself. Keep the URL private, or add MCP auth before
sharing it broadly.

## Windguru direct setup

SurfCheck no longer uses Apify. It reads Windguru's web forecast API directly and
caches forecast rows in memory to avoid repeated Windguru requests on every GPT
question. Some Windguru spot pages only expose wind tabs; for those, SurfCheck
keeps the spot-specific wind forecast and uses a nearby Windguru wave-enabled
spot for swell data.

Set `SURFCHECK_ACCESS_TOKEN` in Render to protect the Siri Shortcut and Action
endpoints.

Optional Render environment variables:

```sh
WINDGURU_CACHE_TTL_SECONDS=10800
WINDGURU_SPOTS_PER_BATCH=4
WINDGURU_WAVE_FALLBACK_SPOT_ID=501140
```

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

## Use from ChatGPT mobile without Siri

The best non-Siri option is a Custom GPT with an Action. This works in normal
ChatGPT chat on iPhone, so you can type or use iPhone keyboard dictation. ChatGPT
Voice Mode still does not run custom actions.

1. Deploy this app.
2. Open ChatGPT on web and create a GPT.
3. Name it `SurfCheck`.
4. In Instructions, paste:

```text
You are SurfCheck. When the user asks about surf spots near Peniche, you MUST use the SurfCheck action before answering. SurfCheck action results are the only allowed live forecast source. Do not answer surf-condition questions from memory, browsing, web search, Windy, Surfline, Apify, or general knowledge. Use the action response's source_policy/source fields as provenance and state that the source is Windguru direct only. If ok is false, best_spot is null, or the action fails, say SurfCheck could not fetch Windguru forecast data and do not make a surf recommendation. Always explain the best spot, the score, the main reasons, and 2-3 alternatives when Windguru data is available. If the user asks for a future time, pass it as the at parameter, e.g. tomorrow 9am. If unsure, pass the full user question as the question parameter.
```

5. Add an Action.
6. Import schema from:
   `https://your-render-service.onrender.com/openapi-action.json`
7. Authentication: API Key.
8. Auth type: Custom.
9. Custom header name:
   `X-SurfCheck-Token`
10. API key value:
   your `SURFCHECK_ACCESS_TOKEN`
11. Save the GPT.

On iPhone, open that GPT and ask:

```text
What is the best spot tomorrow at 9am?
Why not Lagide?
Give me the top 3 for beginner-friendly waves this afternoon.
```

For the Action test panel, try:

```text
question = what is the best spot tomorrow at 9am?
```

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
