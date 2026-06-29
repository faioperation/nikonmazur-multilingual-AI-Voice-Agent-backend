import csv
import io
import requests
from collections import defaultdict

from django.conf import settings

SHEET_ID = settings.GOOGLE_SHEET_ID
GID = settings.GOOGLE_SHEET_GID

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
)


def load_inventory():

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

    inventory = defaultdict(list)

    for row in reader:

        try:
            stock = int(row[stock_idx])
        except Exception:
            stock = 0

        inventory[row[model_idx]].append(
            {
                "color": row[color_idx],
                "interior": row[interior_idx],
                "stock": stock,
            }
        )

    return inventory


def check_availability(model_name: str):

    inventory = load_inventory()

    if not model_name:
        return "No model name was provided."

    query = model_name.lower().strip()

    matched = {}

    for model, variants in inventory.items():

        if query in model.lower() or model.lower() in query:
            matched[model] = variants

    if not matched:
        return f"No availability information found for {model_name}."

    result = []

    for model, variants in matched.items():

        available = [v for v in variants if v["stock"] > 0]

        if not available:
            result.append(f"{model} is currently out of stock.")
            continue

        colours = ", ".join(
            f"{v['color']} (interior: {v['interior']}, stock: {v['stock']})"
            for v in available
        )

        result.append(f"{model} is available. Available variants: {colours}.")

    return "\n".join(result)
