"""Deterministic, dependency-free SVG charts for premium reports."""

from html import escape


def bar_chart(items: list[dict], color: str) -> str | None:
    values = []
    for item in items[:12]:
        raw = item.get("value", item.get("weight_kg", item.get("count")))
        if isinstance(raw, (int, float)) and raw >= 0:
            values.append((str(item.get("label", item.get("name", "Dato")))[:40], float(raw)))
    if not values or max(value for _, value in values) <= 0:
        return None
    maximum = max(value for _, value in values)
    rows = []
    for index, (label, value) in enumerate(values):
        y = 18 + index * 34
        width = 430 * value / maximum
        rows.append(
            f'<text x="0" y="{y + 15}" font-size="12">{escape(label)}</text><rect x="145" y="{y}" width="{width:.1f}" height="20" rx="4" fill="{color}"/><text x="{155 + width:.1f}" y="{y + 15}" font-size="11">{value:g}</text>'
        )
    height = 30 + len(values) * 34
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 {height}" role="img">{"".join(rows)}</svg>'
