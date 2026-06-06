"""Fetch the top ~1,000 games on Steam (by owner estimate) from the SteamSpy API
and cache them to data/steam_games.csv.

SteamSpy's `all` endpoint returns games in pages of 1,000, ordered by owners.
Page 0 is therefore the 1,000 most-owned games on Steam — a clean, well-populated
sample for analysis. The API is free and requires no key.

Usage:
    python fetch_data.py
"""

import csv
import json
import os
import urllib.request
import urllib.error

API_URL = "https://steamspy.com/api.php?request=all&page=0"
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "steam_games.csv")

# Columns we keep. SteamSpy also returns `tags` (a dict) and rank fields we don't need.
COLUMNS = [
    "appid", "name", "developer", "publisher",
    "positive", "negative", "userscore",
    "owners", "average_forever", "median_forever", "ccu",
    "price", "initialprice", "discount",
    "genre", "languages",
]


def fetch() -> dict:
    """Return SteamSpy's page-0 payload as a dict keyed by appid (string)."""
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "steam-games-eda/1.0 (portfolio project)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    print(f"Fetching: {API_URL}")
    try:
        payload = fetch()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error talking to SteamSpy: {exc}")

    games = list(payload.values())
    if not games:
        raise SystemExit("SteamSpy returned no rows — try again later.")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for game in games:
            writer.writerow({col: game.get(col, "") for col in COLUMNS})

    print(f"Wrote {len(games)} games -> {os.path.relpath(OUT_PATH)}")


if __name__ == "__main__":
    main()
