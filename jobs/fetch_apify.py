import os
from typing import Any

import requests
from dotenv import load_dotenv

APIFY_ACTOR_ID = "fortuitous_pirate~windguru-forecast-agent"
APIFY_DATASET_URL = (
    f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"
)


class ApifyForecastError(RuntimeError):
    pass


def fetch_windguru_forecast(spot_id: int, *, timeout: int = 60) -> Any:
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise ApifyForecastError("APIFY_TOKEN is not set")

    response = requests.post(
        APIFY_DATASET_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"stationId": spot_id},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
