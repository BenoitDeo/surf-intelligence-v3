def wind_score(data, spot):
    wind_speed = data["wind_speed_kmh"]
    wind_dir = data["wind_direction"]

    score = 5

    if wind_dir in spot["preferred_wind_dirs"]:
        score += 3
    elif wind_dir in spot["bad_wind_dirs"]:
        score -= 3

    if wind_speed < 13:
        score += 2
    elif wind_speed > 29:
        score -= 3

    return max(0, min(10, score))
