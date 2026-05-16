import json
from engine.scoring import evaluate_spot

def load_data():
    with open("data/cache.json") as f:
        return json.load(f)

def get_best_spot():

    data = load_data()

    best = None
    best_score = 0
    results = []

    for spot, d in data["data"].items():

        res = evaluate_spot(spot, d)
        results.append(res)

        if res["total_score"] > best_score:
            best_score = res["total_score"]
            best = res

    return {
        "best_spot": best,
        "all_spots": results
    }