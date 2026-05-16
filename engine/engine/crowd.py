def crowd_score(data):

    swell = data["swellHeight"]
    wind = data["windSpeed"]

    score = 5

    if 1.3 <= swell <= 2.2 and wind < 12:
        score += 3

    if swell > 3:
        score -= 2

    return max(0, min(10, score))