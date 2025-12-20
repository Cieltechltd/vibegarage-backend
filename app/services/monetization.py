def check_artist_eligibility(
    total_streams: int,
    total_followers: int
) -> bool:
    if total_streams >= 10000:
        return True
    if total_followers >= 150:
        return True
    return False

def calculate_revenue(
    total_streams: int,
    revenue_per_stream: float = 0.0005
) -> float:
    return total_streams * revenue_per_stream  