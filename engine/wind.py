def wind_score(data):
    wind_speed = data["windSpeed"]
    wind_dir = data["windDir"]

    score = 5

    if wind_dir in ["NE", "E"]:
        score += 3
    elif wind_dir in ["W", "SW", "S"]:
        score -= 3

    if wind_speed < 8:
        score += 2
    elif wind_speed > 18:
        score -= 3

    return max(0, min(10, score))