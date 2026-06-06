"""Interactive dashboard for the top most-owned Steam games.

Run locally:
    streamlit run app.py

Data comes from data/steam_games_detailed.csv (built by fetch_data.py + enrich_data.py).
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "steam_games_detailed.csv")

st.set_page_config(page_title="Steam Games Explorer", page_icon="🎮", layout="wide")


def owners_midpoint(raw: str) -> float:
    try:
        lo, hi = (int(p.replace(",", "").strip()) for p in str(raw).split(".."))
        return (lo + hi) / 2
    except (ValueError, TypeError):
        return float("nan")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["owners_est"] = df["owners"].map(owners_midpoint)
    df["reviews_total"] = df["positive"].fillna(0) + df["negative"].fillna(0)
    df["review_score"] = (df["positive"] / df["reviews_total"] * 100).where(df["reviews_total"] > 0)
    df["price_usd"] = pd.to_numeric(df["price"], errors="coerce").fillna(0) / 100
    df["is_free"] = df["price_usd"].eq(0)
    df["price_type"] = df["is_free"].map({True: "Free-to-play", False: "Paid"})
    df["playtime_hours"] = pd.to_numeric(df["average_forever"], errors="coerce").fillna(0) / 60
    df["primary_genre"] = (
        df["genre"].fillna("").str.split(",").str[0].str.strip().replace("", "Unknown")
    )
    return df[df["reviews_total"] >= 50].copy()


df = load_data()

st.title("🎮 Steam Games Explorer")
st.markdown(
    "What separates a highly-rated, widely-played Steam game from the rest? "
    "Explore review scores, ownership, pricing, and genre across the most-owned games on Steam. "
    "Data: [SteamSpy](https://steamspy.com) (free API)."
)

# --------------------------------------------------------------------------- #
# Sidebar filters
# --------------------------------------------------------------------------- #
st.sidebar.header("Filters")
genres = sorted(df["primary_genre"].unique())
picked = st.sidebar.multiselect("Primary genre", genres, default=genres)
price_type = st.sidebar.radio("Pricing", ["All", "Free-to-play", "Paid"], index=0)
min_reviews = st.sidebar.slider(
    "Minimum reviews", 50, int(df["reviews_total"].max()), 50, step=50
)

view = df[df["primary_genre"].isin(picked) & (df["reviews_total"] >= min_reviews)]
if price_type != "All":
    view = view[view["price_type"] == price_type]

if view.empty:
    st.warning("No games match these filters. Loosen them in the sidebar.")
    st.stop()

# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
c1, c2, c3, c4 = st.columns(4)
c1.metric("Games", f"{len(view):,}")
c2.metric("Median review score", f"{view['review_score'].median():.0f}%")
c3.metric("Median owners", f"{view['owners_est'].median()/1e6:.1f}M")
c4.metric("Free-to-play", f"{view['is_free'].mean()*100:.0f}%")

# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
left, right = st.columns(2)

with left:
    st.subheader("Review score distribution")
    fig = px.histogram(view, x="review_score", nbins=24, color="price_type",
                       labels={"review_score": "% positive reviews"})
    fig.update_layout(legend_title_text="", bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Ownership vs review score")
    fig = px.scatter(
        view, x="review_score", y="owners_est", color="price_type",
        size="reviews_total", size_max=22, hover_name="name", log_y=True,
        labels={"review_score": "% positive reviews", "owners_est": "Estimated owners",
                "reviews_total": "Reviews"},
    )
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

left2, right2 = st.columns(2)

with left2:
    st.subheader("Most common genres")
    counts = view["primary_genre"].value_counts().head(12).reset_index()
    counts.columns = ["genre", "games"]
    fig = px.bar(counts, x="games", y="genre", orientation="h")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with right2:
    st.subheader("Median review score by genre")
    top = view["primary_genre"].value_counts().head(10).index
    med = (
        view[view["primary_genre"].isin(top)]
        .groupby("primary_genre")["review_score"].median()
        .sort_values().reset_index()
    )
    fig = px.bar(med, x="review_score", y="primary_genre", orientation="h",
                 labels={"review_score": "% positive", "primary_genre": "genre"})
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# Table
# --------------------------------------------------------------------------- #
st.subheader("Top games by estimated owners")
table = (
    view.nlargest(20, "owners_est")[
        ["name", "primary_genre", "price_type", "review_score", "reviews_total", "owners_est"]
    ]
    .rename(columns={
        "name": "Game", "primary_genre": "Genre", "price_type": "Pricing",
        "review_score": "Review %", "reviews_total": "Reviews", "owners_est": "Est. owners",
    })
)
table["Review %"] = table["Review %"].round(0)
table["Reviews"] = table["Reviews"].astype(int)
table["Est. owners"] = (table["Est. owners"] / 1e6).round(1).astype(str) + "M"
st.dataframe(table, use_container_width=True, hide_index=True)

st.caption("Source: SteamSpy. Sample = most-owned titles on Steam. Built with pandas, Plotly, and Streamlit.")
