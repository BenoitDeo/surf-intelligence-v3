import os

from dotenv import load_dotenv
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from engine.router import get_best_spot
from mcp_server import app as mcp_app


load_dotenv()


def _verify_access_token(request):
    expected = os.getenv("SURFCHECK_ACCESS_TOKEN")
    if expected and request.query_params.get("token") != expected:
        return JSONResponse({"detail": "Invalid access token"}, status_code=401)
    return None


async def health(request):
    return JSONResponse({"status": "ok"})


async def surf(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    result = get_best_spot()
    if not result["best_spot"]:
        return JSONResponse(
            {"message": "No surf forecast could be fetched", "errors": result["errors"]},
            status_code=502,
        )
    return JSONResponse(result)


async def voice(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    result = get_best_spot()
    if not result["best_spot"]:
        return PlainTextResponse("I could not fetch enough current surf data right now.")
    return PlainTextResponse(result["summary"])


async def shortcut(request):
    unauthorized = _verify_access_token(request)
    if unauthorized:
        return unauthorized

    result = get_best_spot()
    text = result["summary"]
    return JSONResponse({"text": text})


app = mcp_app()
app.routes.insert(0, Route("/health", health, methods=["GET"]))
app.routes.insert(0, Route("/surf", surf, methods=["GET"]))
app.routes.insert(0, Route("/voice", voice, methods=["GET"]))
app.routes.insert(0, Route("/shortcut", shortcut, methods=["GET"]))
