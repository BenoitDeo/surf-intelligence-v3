from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from engine.router import SOURCE_POLICY, get_best_spot
from engine.scoring import load_optimal_conditions


load_dotenv()

mcp = FastMCP(
    "SurfCheck",
    instructions=(
        "Use this server to recommend the best current surf spot around "
        "Peniche, Portugal. All live surf recommendations must use Windguru "
        "forecasts fetched through Apify; do not use model memory, web browsing, "
        "direct Windguru calls, Windy, Surfline, or any other source as a "
        "substitute. If Apify data is unavailable, say the forecast is "
        "unavailable instead of answering from another source."
    ),
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def best_surf_spot(include_all_spots: bool = False, target_time: str | None = None) -> dict:
    """Return the best Peniche-area surf spot for now or a requested time like tomorrow 9am."""
    result = get_best_spot(target_time=target_time)
    response = {
        "summary": result["summary"],
        "source_policy": result["source_policy"],
        "best_spot": result["best_spot"],
        "errors": result["errors"],
    }
    if include_all_spots:
        response["all_spots"] = result["all_spots"]
    return response


@mcp.tool()
def list_surf_spots() -> list[dict]:
    """List configured surf spots. This is metadata only, not a live forecast source."""
    return [
        {
            "key": key,
            "name": spot["name"],
            "windguru_spot_id": spot["windguru_spot_id"],
            "has_live_forecast": bool(spot["windguru_spot_id"]),
            "lat": spot["lat"],
            "lon": spot["lon"],
            "live_forecast_source": SOURCE_POLICY["source_name"],
        }
        for key, spot in load_optimal_conditions().items()
    ]


def app():
    return mcp.streamable_http_app()


if __name__ == "__main__":
    import os

    mcp.settings.host = os.getenv("HOST", "0.0.0.0")
    mcp.settings.port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="streamable-http")
