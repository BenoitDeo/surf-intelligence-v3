def swell_score(data, spot):
    h = data["swell_height_m"]
    p = data["swell_period_s"]

    score = 5

    if spot["ideal_swell_min_m"] <= h <= spot["ideal_swell_max_m"]:
        score += 2

    if p >= 12:
        score += 3
    elif p < 8:
        score -= 3

    return max(0, min(10, score))
