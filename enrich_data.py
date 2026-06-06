"""Enrich the top-N most-owned games with per-title detail from SteamSpy.

The bulk `all` endpoint (see fetch_data.py) omits genre, languages, and tags.
Those live on SteamSpy's `appdetails` endpoint, one call per game. We stay polite
(~1 request/second) and cache the result to data/steam_games_detailed.csv.

The top-N rows of data/steam_games.csv are already ordered by owners (most-owned
first), so we simply enrich that prefix. N defaults to 400 and can be overridden:

    python enrich_data.py 400
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "data", "steam_games.csv")
OUT_PATH = os.path.join(HERE, "data", "steam_games_detailed.csv")
DETAILS_URL = "https://steamspy.com/api.php?request=appdetails&appid={appid}"
DELAY_SECONDS = 1.1  # SteamSpy asks for <= 1 request/second on appdetails

COLUMNS = [
    "appid", "name", "developer", "publisher",
    "positive", "negative",
    "owners", "average_forever", "median_forever", "ccu",
    "price", "initialprice", "discount",
    "genre", "tags_top",
]


def read_top_appids(n: int) -> list[str]:
    with open(IN_PATH, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [r["appid"] for r in rows[:n]]


def fetch_details(appid: str) -> dict | None:
    req = urllib.request.Request(
        DETAILS_URL.format(appid=appid),
        headers={"User-Agent": "steam-games-eda/1.0 (portfolio project)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def top_tags(tags) -> str:
    """SteamSpy returns tags as {tag: votes}. Keep the three most-voted names."""
    if not isinstance(tags, dict) or not tags:
        return ""
    ranked = sorted(tags.items(), key=lambda kv: kv[1], reverse=True)
    return ", ".join(name for name, _ in ranked[:3])


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    appids = read_top_appids(n)
    print(f"Enriching {len(appids)} games via SteamSpy appdetails (~{DELAY_SECONDS}s each)...")

    written = 0
    failed = 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for i, appid in enumerate(appids, 1):
            data = fetch_details(appid)
            if data and data.get("name"):
                row = {col: data.get(col, "") for col in COLUMNS}
                row["tags_top"] = top_tags(data.get("tags"))
                writer.writerow(row)
                written += 1
            else:
                failed += 1
            if i % 50 == 0:
                print(f"  {i}/{len(appids)} done ({written} ok, {failed} failed)")
            time.sleep(DELAY_SECONDS)

    print(f"Wrote {written} detailed rows ({failed} failed) -> {os.path.relpath(OUT_PATH)}")


if __name__ == "__main__":
    main()
