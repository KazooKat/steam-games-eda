"""Exploratory analysis of the most-owned Steam games.

Question: what separates a highly-rated, widely-played Steam game from the rest?
We look at how pricing (free-to-play vs paid) and genre relate to two success
signals — the review score (share of positive reviews) and estimated owners.

Cleaning, the review metric, and the colour palette are shared with the live
dashboard via steam_eda.py, so the README charts and the app agree by construction.

Run after fetch_data.py + enrich_data.py:
    python analysis.py

Outputs:
    charts/*.png   — figures used in the README
    FINDINGS.txt   — headline numbers (also printed to stdout)
"""

import os

import matplotlib

matplotlib.use("Agg")  # headless: write PNGs, never open a window
import matplotlib.pyplot as plt
import pandas as pd

import steam_eda as se

HERE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(HERE, "charts")
FINDINGS_PATH = os.path.join(HERE, "FINDINGS.txt")


# --------------------------------------------------------------------------- #
# Shared chart styling (mirrors the dashboard's clean-light look)
# --------------------------------------------------------------------------- #
def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": se.GRID,
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": se.GRID,
            "grid.linewidth": 0.8,
            "font.size": 11,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlecolor": se.INK,
            "axes.labelcolor": se.TEXT,
            "text.color": se.TEXT,
            "xtick.color": se.TEXT,
            "ytick.color": se.TEXT,
        }
    )


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, name), dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  chart -> charts/{name}")


def label_barh(ax, values, fmt="{:.0f}", pad=0.01) -> None:
    """Direct value labels at the end of each horizontal bar."""
    span = ax.get_xlim()[1]
    for bar, value in zip(ax.patches, values):
        ax.text(
            bar.get_width() + span * pad,
            bar.get_y() + bar.get_height() / 2,
            fmt.format(value),
            va="center",
            ha="left",
            fontsize=10,
            color=se.TEXT,
        )


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def chart_rating_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    scores = df["review_score"].dropna()
    ax.hist(scores, bins=24, color=se.ACCENT, edgecolor="white")
    med = scores.median()
    ax.axvline(med, color=se.INK, linestyle="--", linewidth=1.2)
    ax.text(med - 1, ax.get_ylim()[1] * 0.95, f"median {med:.0f}%", ha="right", va="top", color=se.INK)
    ax.set_title("Most top games score 70–95% positive")
    ax.set_xlabel("% positive reviews")
    ax.set_ylabel("Number of games")
    save(fig, "rating_distribution.png")


def chart_free_vs_paid(df: pd.DataFrame) -> None:
    """Honest pricing comparison: review quality only.

    Median owners are roughly equal across paid/free in this sample (owner counts
    are banded), so free-to-play's real reach advantage is in the *extreme top*,
    not the median — that is left to the scatter rather than charted as a median.
    """
    order = ["Paid", "Free-to-play"]
    raw = df.groupby("price_type")["review_score"].median().reindex(order)
    wilson = df.groupby("price_type")["rating_quality"].median().reindex(order)

    x = range(len(order))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar([i - width / 2 for i in x], raw.values, width, label="Raw % positive", color=se.NEUTRAL)
    b2 = ax.bar([i + width / 2 for i in x], wilson.values, width, label="Reliable (Wilson)", color=se.ACCENT)
    ax.bar_label(b1, fmt="%.0f%%", padding=3, color=se.TEXT)
    ax.bar_label(b2, fmt="%.0f%%", padding=3, color=se.TEXT)
    ax.set_xticks(list(x))
    ax.set_xticklabels(order)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Median review score")
    ax.set_title("Paid games rate higher than free-to-play")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "free_vs_paid.png")


def chart_top_genres(df: pd.DataFrame) -> None:
    counts = df["primary_genre"].value_counts().head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(counts.index, counts.values, color=se.ACCENT)
    ax.margins(x=0.12)
    label_barh(ax, counts.values, fmt="{:.0f}")
    ax.set_title("Action dominates the most-owned catalog")
    ax.set_xlabel("Number of games")
    save(fig, "top_genres.png")


def chart_rating_by_genre(df: pd.DataFrame) -> None:
    top = (
        df.groupby("primary_genre")
        .filter(lambda g: len(g) >= 5)
        .groupby("primary_genre")["rating_quality"]
        .median()
        .sort_values()
        .tail(10)
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top.index, top.values, color=se.ACCENT)
    ax.set_xlim(0, 100)  # full 0–100 axis: do not exaggerate small gaps
    label_barh(ax, top.values, fmt="{:.0f}%", pad=0.015)
    ax.set_title("Indie & strategy are the best-loved genres")
    ax.set_xlabel("Median reliable rating, % (Wilson lower bound)")
    save(fig, "rating_by_genre.png")


def chart_owners_vs_rating(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sub = df.dropna(subset=["owners_est", "review_score"])
    colors = sub["is_free"].map({True: se.FREE, False: se.PAID})
    ax.scatter(sub["review_score"], sub["owners_est"], c=colors, alpha=0.6, edgecolor="white", linewidth=0.3)
    ax.set_yscale("log")
    ax.set_title("Reach and reception are largely independent")
    ax.set_xlabel("% positive reviews")
    ax.set_ylabel("Estimated owners (log scale)")
    handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", color=se.PAID, label="Paid"),
        plt.Line2D([0], [0], marker="o", linestyle="", color=se.FREE, label="Free-to-play"),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower left")
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
        .groupby("primary_genre")["rating_quality"]
        .median()
        .sort_values(ascending=False)
        .head(5)
    )
    top_devs = df.groupby("developer")["owners_est"].sum().sort_values(ascending=False).head(5)

    lines = [
        f"Sample: {n} of the most-owned games on Steam (>= {se.MIN_REVIEWS} reviews).",
        f"Free-to-play share: {free_share:.0f}%.",
        f"Median review score (raw % positive) - paid: {paid['review_score'].median():.1f}% | free: {free['review_score'].median():.1f}%.",
        f"Median reliable rating (Wilson) - paid: {paid['rating_quality'].median():.1f}% | free: {free['rating_quality'].median():.1f}%.",
        f"Median estimated owners - paid: {paid['owners_est'].median()/1e6:.1f}M | free: {free['owners_est'].median()/1e6:.1f}M (banded, so roughly equal).",
        f"Price vs review-score correlation (paid games): {corr:+.2f}.",
        "Most common genres: " + ", ".join(f"{g} ({c})" for g, c in top_genres.items()) + ".",
        "Best-loved genres (Wilson median, >=5 titles): " + ", ".join(f"{g} {v:.0f}%" for g, v in best_genres.items()) + ".",
        "Biggest developers by total owners: " + ", ".join(f"{d} ({v/1e6:.0f}M)" for d, v in top_devs.items()) + ".",
        "Note: SteamSpy owner counts are banded ranges, so owner medians are coarse — review scores are the more reliable signal.",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(CHART_DIR, exist_ok=True)
    apply_style()
    df = se.load_data()
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
