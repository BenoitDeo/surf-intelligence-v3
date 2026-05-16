from engine.wind import wind_score
from engine.swell import swell_score
from engine.tide import tide_score
from engine.crowd import crowd_score


def evaluate_spot(spot_id, spot, forecast):
    wind = wind_score(forecast, spot)
    swell = swell_score(forecast, spot)
    tide = tide_score(spot)
    crowd = crowd_score(forecast)

    total = (wind * 0.3) + (swell * 0.3) + (tide * 0.2) + ((10 - crowd) * 0.2)

    return {
        "spot": spot_id,
        "name": spot["name"],
        "forecast": forecast,
        "wind": wind,
        "swell": swell,
        "tide": tide,
        "crowd": crowd,
        "total_score": round(total, 2)
    }
