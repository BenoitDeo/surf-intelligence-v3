from engine.wind import wind_score
from engine.swell import swell_score
from engine.tide import tide_score
from engine.crowd import crowd_score

def evaluate_spot(spot, data):

    wind = wind_score(data)
    swell = swell_score(data)
    tide = tide_score(spot)
    crowd = crowd_score(data)

    total = (wind * 0.3) + (swell * 0.3) + (tide * 0.2) + ((10 - crowd) * 0.2)

    return {
        "spot": spot,
        "wind": wind,
        "swell": swell,
        "tide": tide,
        "crowd": crowd,
        "total_score": round(total, 2)
    }