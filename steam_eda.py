"""Shared data layer + design tokens for the Steam games project.

Both the static analysis (`analysis.py`) and the interactive dashboard (`app.py`)
import from here, so the cleaning rules, the review-quality metric, and the colour
palette stay identical across the README charts and the live app. One source of
truth is what keeps the two surfaces telling the *same* story.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "steam_games_detailed.csv")

# Below this many reviews a positive-share score is too noisy to trust, so those
# titles are dropped before any rating is computed.
MIN_REVIEWS = 50

# Genre tokens that describe pricing/status rather than a real genre. They are
# stripped when picking a primary genre so "Action, Free To Play" -> "Action".
_STATUS_TOKENS = {"free to play", "early access"}


# --------------------------------------------------------------------------- #
# Design tokens — clean-light theme. Blue/amber is a colour-blind-safe pair,
# and the same hues are reused everywhere a paid/free split appears.
# --------------------------------------------------------------------------- #
ACCENT = "#2563EB"   # primary blue — highlighted series, single-series bars
PAID = "#2563EB"     # paid games (matches accent)
FREE = "#F59E0B"     # free-to-play (amber)
NEUTRAL = "#94A3B8"  # slate-400 — context / non-highlighted marks
INK = "#0F172A"      # slate-900 — titles
TEXT = "#1F2933"     # body text
GRID = "#E2E8F0"     # slate-200 — gridlines / borders
PANEL = "#F4F6F8"    # card / secondary background
FONT_FAMILY = "Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

# Semantic colour map used by every chart that splits on pricing.
PRICE_COLORS = {"Paid": PAID, "Free-to-play": FREE}
PRICE_ORDER = ["Paid", "Free-to-play"]


# --------------------------------------------------------------------------- #
# Cleaning helpers
# --------------------------------------------------------------------------- #
def owners_midpoint(raw: str) -> float:
    """'100,000,000 .. 200,000,000' -> 150000000.0 (NaN if unparseable)."""
    try:
        lo, hi = (int(part.replace(",", "").strip()) for part in str(raw).split(".."))
        return (lo + hi) / 2
    except (ValueError, TypeError):
        return float("nan")


def primary_genre(raw: str) -> str:
    """First real genre token, ignoring pricing/status labels; else 'Unknown'."""
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    real = [p for p in parts if p.lower() not in _STATUS_TOKENS]
    return real[0] if real else "Unknown"


def wilson_lower_bound(positive, total, z: float = 1.96) -> np.ndarray:
    """Lower bound of the Wilson score interval for a positive-review share.

    Ranking by raw % positive lets a 10/10 title outrank a 9,000/10,000 one,
    even though the latter is far more certainly good. The Wilson lower bound
    folds the *sample size* into the score: small-n titles are pulled toward
    0.5, large-n titles stay near their observed rate. This is the standard
    "how not to sort by average rating" fix (Evan Miller, 2009).

    Returns a 0..1 array (NaN where there are no reviews). Vectorised over
    array-like ``positive`` and ``total``.
    """
    positive = np.asarray(positive, dtype=float)
    total = np.asarray(total, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        phat = positive / total
        z2 = z * z
        denominator = 1.0 + z2 / total
        centre = phat + z2 / (2.0 * total)
        margin = z * np.sqrt((phat * (1.0 - phat) + z2 / (4.0 * total)) / total)
        lower = (centre - margin) / denominator
    return np.where(total > 0, lower, np.nan)


def load_data() -> pd.DataFrame:
    """Load and clean the enriched SteamSpy snapshot into an analysis-ready frame.

    Adds: owners_est, reviews_total, review_score (raw % positive),
    rating_quality (Wilson lower bound, 0-100), price_usd, is_free, price_type,
    and primary_genre. Drops titles below ``MIN_REVIEWS`` so every score is
    backed by enough reviews to mean something.
    """
    df = pd.read_csv(DATA_PATH)

    df["owners_est"] = df["owners"].map(owners_midpoint)

    positive = pd.to_numeric(df["positive"], errors="coerce").fillna(0)
    negative = pd.to_numeric(df["negative"], errors="coerce").fillna(0)
    df["reviews_total"] = positive + negative
    df["review_score"] = (positive / df["reviews_total"] * 100).where(df["reviews_total"] > 0)
    df["rating_quality"] = wilson_lower_bound(positive, df["reviews_total"]) * 100

    df["price_usd"] = pd.to_numeric(df["price"], errors="coerce").fillna(0) / 100
    df["is_free"] = df["price_usd"].eq(0)
    df["price_type"] = df["is_free"].map({True: "Free-to-play", False: "Paid"})

    df["primary_genre"] = df["genre"].fillna("").map(primary_genre)

    return df[df["reviews_total"] >= MIN_REVIEWS].copy()
