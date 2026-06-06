"""Exploratory analysis of the top most-owned Steam games.

Question: what separates a highly-rated, widely-played Steam game from the rest?
We look at how pricing (free-to-play vs paid), genre, and review volume relate to
two success signals: the review score (share of positive reviews) and the estimated
owner count.

Run after fetch_data.py + enrich_data.py:
    python analysis.py

Outputs:
    charts/*.png   — figures used in the README
    FINDINGS.txt   — headline numbers (also printed to stdout)
"""

import os
import textwrap

import matplotlib
matplotlib.use("Agg")  # headless: write PNGs, never open a window
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(__file__)
DATA_PATH = os.path.join(HERE, "data", "steam_games_detailed.csv")
CHART_DIR = os.path.join(HERE, "charts")
FINDINGS_PATH = os.path.join(HERE, "FINDINGS.txt")

MIN_REVIEWS = 50  # ignore games with too few reviews to score reliably


# --------------------------------------------------------------------------- #
# Load + clean
# --------------------------------------------------------------------------- #
def owners_midpoint(raw: str) -> float:
    """'100,000,000 .. 200,000,000' -> 150000000.0"""
    try:
        lo, hi = (int(part.replace(",", "").strip()) for part in str(raw).split(".."))
        return (lo + hi) / 2
    except (ValueError, TypeError):
        return float("nan")


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["owners_est"] = df["owners"].map(owners_midpoint)
    df["reviews_total"] = df["positive"].fillna(0) + df["negative"].fillna(0)
    df["review_score"] = (df["positive"] / df["reviews_total"] * 100).where(df["reviews_total"] > 0)
    df["price_usd"] = pd.to_numeric(df["price"], errors="coerce").fillna(0) / 100
    df["is_free"] = df["price_usd"].eq(0)
    df["playtime_hours"] = pd.to_numeric(df["average_forever"], errors="coerce").fillna(0) / 60
    df["primary_genre"] = (
        df["genre"].fillna("").str.split(",").str[0].str.strip().replace("", pd.NA)
    )
    return df[df["reviews_total"] >= MIN_REVIEWS].copy()


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def save(fig, name: str) -> None:
    path = os.path.join(CHART_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  chart -> charts/{name}")


def chart_rating_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(df["review_score"].dropna(), bins=24, color="#1b6ca8", edgecolor="white")
    ax.set_title("Review score distribution (top owned Steam games)")
    ax.set_xlabel("% positive reviews")
    ax.set_ylabel("Number of games")
    save(fig, "rating_distribution.png")


def chart_free_vs_paid(df: pd.DataFrame) -> None:
    grp = df.groupby("is_free")
    labels = ["Paid", "Free-to-play"]
    rating = [grp.get_group(False)["review_score"].median(), grp.get_group(True)["review_score"].median()]
    owners = [grp.get_group(False)["owners_est"].median() / 1e6, grp.get_group(True)["owners_est"].median() / 1e6]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.5))
    a1.bar(labels, rating, color=["#1b6ca8", "#28a745"])
    a1.set_title("Median review score")
    a1.set_ylabel("% positive")
    a2.bar(labels, owners, color=["#1b6ca8", "#28a745"])
    a2.set_title("Median estimated owners")
    a2.set_ylabel("Millions of owners")
    fig.suptitle("Free-to-play vs paid", fontweight="bold")
    save(fig, "free_vs_paid.png")


def chart_top_genres(df: pd.DataFrame) -> None:
    counts = df["primary_genre"].value_counts().head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(counts.index, counts.values, color="#1b6ca8")
    ax.set_title("Most common primary genres")
    ax.set_xlabel("Number of games")
    save(fig, "top_genres.png")


def chart_rating_by_genre(df: pd.DataFrame) -> None:
    top = df["primary_genre"].value_counts().head(10).index
    med = (
        df[df["primary_genre"].isin(top)]
        .groupby("primary_genre")["review_score"].median()
        .sort_values()
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(med.index, med.values, color="#28a745")
    ax.set_xlim(left=min(60, med.min() - 5))
    ax.set_title("Median review score by genre (top 10 genres)")
    ax.set_xlabel("% positive reviews")
    save(fig, "rating_by_genre.png")


def chart_owners_vs_rating(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sub = df.dropna(subset=["owners_est", "review_score"])
    colors = sub["is_free"].map({True: "#28a745", False: "#1b6ca8"})
    ax.scatter(sub["review_score"], sub["owners_est"], c=colors, alpha=0.6, edgecolor="white", linewidth=0.3)
    ax.set_yscale("log")
    ax.set_title("Ownership vs review score (green = free-to-play)")
    ax.set_xlabel("% positive reviews")
    ax.set_ylabel("Estimated owners (log scale)")
    save(fig, "owners_vs_rating.png")


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #
def findings(df: pd.DataFrame) -> str:
    n = len(df)
    free_share = df["is_free"].mean() * 100
    paid = df[~df["is_free"]]
    free = df[df["is_free"]]
    corr = paid["price_usd"].corr(paid["review_score"])
    top_genres = df["primary_genre"].value_counts().head(5)
    best_genres = (
        df.groupby("primary_genre")
        .filter(lambda g: len(g) >= 5)
        .groupby("primary_genre")["review_score"].median()
        .sort_values(ascending=False).head(5)
    )
    top_devs = df.groupby("developer")["owners_est"].sum().sort_values(ascending=False).head(5)

    lines = []
    lines.append(f"Sample: {n} of the most-owned games on Steam (>= {MIN_REVIEWS} reviews).")
    lines.append(f"Free-to-play share: {free_share:.0f}%.")
    lines.append(f"Median review score - paid: {paid['review_score'].median():.1f}% | free: {free['review_score'].median():.1f}%.")
    lines.append(f"Median owners - paid: {paid['owners_est'].median()/1e6:.1f}M | free: {free['owners_est'].median()/1e6:.1f}M.")
    lines.append(f"Price vs review-score correlation (paid games): {corr:+.2f}.")
    lines.append("Most common genres: " + ", ".join(f"{g} ({c})" for g, c in top_genres.items()) + ".")
    lines.append("Highest-rated genres (median): " + ", ".join(f"{g} {v:.0f}%" for g, v in best_genres.items()) + ".")
    lines.append("Biggest developers by total owners: " + ", ".join(f"{d} ({v/1e6:.0f}M)" for d, v in top_devs.items()) + ".")
    lines.append("(Note: SteamSpy owner counts are banded, so owner medians are coarse — review scores are the more reliable signal.)")
    return "\n".join(lines)


def main() -> None:
    os.makedirs(CHART_DIR, exist_ok=True)
    df = load()
    print(f"Loaded {len(df)} scored games.\n")

    chart_rating_distribution(df)
    chart_free_vs_paid(df)
    chart_top_genres(df)
    chart_rating_by_genre(df)
    chart_owners_vs_rating(df)

    report = findings(df)
    with open(FINDINGS_PATH, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    print("\n" + "=" * 70 + "\nFINDINGS\n" + "=" * 70)
    print(report)


if __name__ == "__main__":
    main()
