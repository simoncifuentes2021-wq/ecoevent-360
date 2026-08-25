from decimal import Decimal


def compare(baseline, comparison, *, kind: str = "VALUE") -> dict:
    first, second = Decimal(str(baseline)), Decimal(str(comparison))
    difference = second - first
    percentage = None if first == 0 else (difference / abs(first) * Decimal(100))
    points = difference if kind == "PERCENTAGE" else None
    return {
        "baseline": float(first),
        "comparison": float(second),
        "absolute_difference": float(difference),
        "percentage_difference": float(percentage) if percentage is not None else None,
        "percentage_point_change": float(points) if points is not None else None,
        "trend": "UP" if difference > 0 else "DOWN" if difference < 0 else "STABLE",
    }
