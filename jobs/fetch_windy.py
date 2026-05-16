import os
import requests
import json
from config.spots import SPOTS

API_KEY = os.getenv("WINDY_API_KEY")

def fetch(lat, lon):
    url = "https://api.windy.com/api/point-forecast/v2"

    params = {
        "lat": lat,
        "lon": lon,
        "model": "gfs",
        "parameters": ["wind", "waves", "wavePeriod", "windDir"],
        "key": API_KEY
    }

    return requests.get(url, params=params).json()

def run():
    data = {}

    for spot, c in SPOTS.items():
        data[spot] = fetch(c["lat"], c["lon"])

    with open("data/cache.json", "w") as f:
        json.dump({"data": data}, f)

if __name__ == "__main__":
    run()