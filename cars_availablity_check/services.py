import csv
import io
import requests
from collections import defaultdict
from django.core.cache import cache
from django.conf import settings

SHEET_ID = settings.GOOGLE_SHEET_ID
GID = settings.GOOGLE_SHEET_GID
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
)

CACHE_KEY = "cars_sheet"
CACHE_TIMEOUT = 3600  # 1 hour


def get_all_cars():

    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    response = requests.get(CSV_URL, timeout=10)
    response.raise_for_status()

    csv_file = io.StringIO(response.content.decode("utf-8", errors="replace"))
    reader = csv.reader(csv_file)

    headers = next(reader)

    model_idx = headers.index("Verkaufsmodell")
    stock_idx = headers.index("Standtage")

    interior_idx = next(
        i for i, h in enumerate(headers) if "Innenausf" in h and "Bezeichnung" in h
    )

    color_idx = next(i for i, h in enumerate(headers) if "Farbe" in h and "Au" in h)

    grouped = defaultdict(list)

    for row in reader:

        try:
            stock = int(row[stock_idx])
        except:
            stock = 0

        grouped[row[model_idx]].append(
            {
                "color": row[color_idx],
                "interior": row[interior_idx],
                "stock": stock,
            }
        )

    lines = []

    for model, cars in grouped.items():

        lines.append(f"{model}:")

        for car in cars:
            lines.append(
                f"  - {car['color']} "
                f"(interior: {car['interior']}) "
                f"— Stock: {car['stock']}"
            )

        lines.append("")

    result = "\n".join(lines)

    cache.set(CACHE_KEY, result, CACHE_TIMEOUT)

    return result
