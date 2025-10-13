def safe_float(value) -> float:
    """
    Safely convert any value to float
    """
    try:
        result = float(value)
        return result if result == result else 0.0  # Check for NaN
    except (ValueError, TypeError):
        return 0.0