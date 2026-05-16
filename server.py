import os

from dotenv import load_dotenv
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from engine.router import get_best_spot
from mcp_server import app as mcp_app


load_dotenv()


def _verify_access_token(request):
    expected = os.getenv("SURFCHECK_ACCESS_TOKEN")
    supplied = request.query_params.get("token") or request.headers.get("x-surfcheck-token")
    if expected and supplied != expected:
        return JSONResponse({"detail": "Invalid access token"}, status_code=401)
    return None


async def health(request):
    return JSONResponse({"status": "ok"})


async def surf(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    try:
        result = get_best_spot(target_time=_target_time_from_request(request))
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "summary": f"SurfCheck could not process that request: {exc}",
                "target_time": None,
                "best_spot": None,
                "all_spots": [],
                "errors": {"request": str(exc)},
            }
        )

    if not result["best_spot"]:
        return JSONResponse(
            {
                "ok": False,
                "summary": "No surf forecast could be fetched. Check APIFY_TOKEN and the Apify actor response.",
                "target_time": result.get("target_time"),
                "best_spot": None,
                "all_spots": [],
                "errors": result["errors"],
            }
        )
    result["ok"] = True
    return JSONResponse(result)


async def voice(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    result = get_best_spot(target_time=_target_time_from_request(request))
    if not result["best_spot"]:
        return PlainTextResponse("I could not fetch enough current surf data right now.")
    return PlainTextResponse(result["summary"])


async def shortcut(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    result = get_best_spot(target_time=_target_time_from_request(request))
    text = result["summary"]
    return JSONResponse({"text": text})


async def openapi_action_schema(request):
    base_url = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "openapi": "3.1.0",
            "info": {
                "title": "SurfCheck",
                "version": "1.0.0",
                "description": (
                    "Recommends the best surf spot around Peniche by comparing "
                    "Windguru forecasts against optimal conditions for each spot."
                ),
            },
            "servers": [{"url": base_url}],
            "paths": {
                "/surf": {
                    "get": {
                        "operationId": "getBestSurfSpot",
                        "summary": "Get the best surf spot for now or a requested time.",
                        "description": (
                            "Use this whenever the user asks for the best surf spot, "
                            "surf forecast, ranking, or what spot to choose near Peniche."
                        ),
                        "parameters": [
                            {
                                "name": "at",
                                "in": "query",
                                "required": False,
                                "description": (
                                    "Requested forecast time in natural language or ISO format. "
                                    "Examples: tomorrow 9am, today 15:00, 2026-05-17T09:00:00+01:00."
                                ),
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "question",
                                "in": "query",
                                "required": False,
                                "description": (
                                    "The user's original question. Use this if the user asks in natural "
                                    "language, for example: what is best tomorrow at 9am?"
                                ),
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Spot recommendation with ranking and reasons.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/SurfRecommendation"
                                        }
                                    }
                                },
                            }
                        },
                        "security": [{"SurfCheckToken": []}],
                    }
                }
            },
            "components": {
                "schemas": {
                    "SurfRecommendation": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "target_time": {
                                "type": "string",
                                "nullable": True,
                            },
                            "best_spot": {"type": "object"},
                            "all_spots": {
                                "type": "array",
                                "items": {"type": "object"},
                            },
                            "errors": {"type": "object"},
                        },
                        "required": ["summary", "best_spot", "all_spots"],
                    }
                },
                "securitySchemes": {
                    "SurfCheckToken": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-SurfCheck-Token",
                    }
                }
            },
        }
    )


app = mcp_app()
app.routes.insert(0, Route("/health", health, methods=["GET"]))
app.routes.insert(0, Route("/openapi-action.json", openapi_action_schema, methods=["GET"]))
app.routes.insert(0, Route("/surf", surf, methods=["GET"]))
app.routes.insert(0, Route("/voice", voice, methods=["GET"]))
app.routes.insert(0, Route("/shortcut", shortcut, methods=["GET"]))


def _target_time_from_request(request):
    return request.query_params.get("at") or request.query_params.get("question")
