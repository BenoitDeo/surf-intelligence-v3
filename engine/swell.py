def swell_score(data):
    h = data["swellHeight"]
    p = data["swellPeriod"]

    score = 5

    if 1.2 <= h <= 2.5:
        score += 2

    if p >= 12:
        score += 3
    elif p < 8:
        score -= 3

    return max(0, min(10, score))