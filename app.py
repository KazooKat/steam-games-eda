"""Interactive dashboard: what separates a great Steam game from the rest?

Run locally:
    streamlit run app.py

Cleaning, the review-quality metric, and the colour palette live in steam_eda.py
so this app and the static README charts stay perfectly in sync.
"""

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

import steam_eda as se

st.set_page_config(
    page_title="Steam Games Explorer",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"about": "Steam Games Explorer — an EDA of the most-owned games on Steam."},
)


# --------------------------------------------------------------------------- #
# Cohesive look: one Plotly template + a little CSS so the app reads as a
# designed product rather than a default Streamlit page.
# --------------------------------------------------------------------------- #
def _plotly_template() -> go.layout.Template:
    axis = dict(
        gridcolor=se.GRID,
        linecolor=se.GRID,
        zeroline=False,
        title_font=dict(size=13, color=se.TEXT),
        tickfont=dict(size=12, color=se.TEXT),
    )
    return go.layout.Template(
        layout=dict(
            font=dict(family=se.FONT_FAMILY, size=13, color=se.TEXT),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=[se.ACCENT, se.FREE, se.NEUTRAL, se.INK],
            xaxis=axis,
            yaxis=axis,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
            margin=dict(l=8, r=8, t=44, b=8),
            hoverlabel=dict(bgcolor="white", bordercolor=se.GRID, font_size=12, font_family=se.FONT_FAMILY),
            colorscale=dict(sequential=[[0.0, "#DBEAFE"], [1.0, se.ACCENT]]),
        )
    )


pio.templates["steam_clean"] = _plotly_template()
pio.templates.default = "steam_clean"

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.3rem; padding-bottom: 3rem; max-width: 1180px;}
      h1, h2, h3 {color: #0F172A; font-weight: 700; letter-spacing: -0.01em;}
      [data-testid="stMetric"] {
          background: #F4F6F8; border: 1px solid #E2E8F0;
          border-radius: 12px; padding: 16px 18px;
      }
      [data-testid="stMetricValue"] {font-size: 1.7rem; color: #0F172A;}
      [data-testid="stMetricLabel"] p {color: #475569; font-weight: 600;}
      section[data-testid="stSidebar"] {background: #F8FAFC; border-right: 1px solid #E2E8F0;}
      hr {margin: 1.1rem 0; border-color: #E2E8F0;}
      #MainMenu, footer, [data-testid="stDecoration"] {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_data():
    return se.load_data()


df = get_data()


def styled(fig):
    """Final polish applied to every figure after px builds it."""
    fig.update_layout(margin=dict(l=8, r=8, t=44, b=8))
    fig.update_traces(marker_line_width=0)
    return fig


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("🎮 Steam Games Explorer")
st.markdown(
    "#### What separates a highly-rated, widely-played Steam game from the rest?\n"
    "Explore review quality, ownership, pricing, and genre across the most-owned games "
    "on Steam. Use the filters on the left to slice the catalog."
)

# --------------------------------------------------------------------------- #
# Sidebar filters
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Filters")
    genres = sorted(df["primary_genre"].unique())
    picked = st.multiselect("Primary genre", genres, default=genres)
    price_type = st.radio("Pricing", ["All", "Free-to-play", "Paid"], index=0)
    min_reviews = st.slider(
        "Minimum reviews",
        int(se.MIN_REVIEWS),
        int(df["reviews_total"].max()),
        int(se.MIN_REVIEWS),
        step=50,
        help="Games with fewer reviews than this are hidden — their scores are noisier.",
    )

    st.divider()
    st.markdown(
        "**About**  \nA single live snapshot of the 400 most-owned games on Steam, "
        "via the free [SteamSpy](https://steamspy.com) API.\n\n"
        "Ratings use the **Wilson lower-bound** score, which discounts titles with "
        "few reviews so a 10/10 game can't outrank a 9,000/10,000 one."
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
c1.metric("Games in view", f"{len(view):,}")
c2.metric("Median rating", f"{view['review_score'].median():.0f}%", help="Raw share of positive reviews.")
c3.metric(
    "Median reliable rating",
    f"{view['rating_quality'].median():.0f}%",
    help="Wilson lower-bound score — a sample-size-aware rating, the more honest signal.",
)
c4.metric("Free-to-play", f"{view['is_free'].mean() * 100:.0f}%")

st.divider()

# --------------------------------------------------------------------------- #
# Section 1 — the thesis: reach vs. reception
# --------------------------------------------------------------------------- #
st.subheader("Reach and reception are two different games")
st.caption(
    "Estimated owners vs. review score. The cloud is wide, not a line — titles can be "
    "massively owned *and* divisive (big shooters), or modestly owned *and* beloved (indies)."
)
fig = px.scatter(
    view,
    x="review_score",
    y="owners_est",
    color="price_type",
    color_discrete_map=se.PRICE_COLORS,
    category_orders={"price_type": se.PRICE_ORDER},
    size="reviews_total",
    size_max=26,
    opacity=0.7,
    hover_name="name",
    log_y=True,
    labels={
        "review_score": "% positive reviews",
        "owners_est": "Estimated owners (log scale)",
        "reviews_total": "Reviews",
        "price_type": "",
    },
)
fig.update_layout(yaxis_title="Estimated owners (log scale)")
st.plotly_chart(styled(fig), width="stretch")

st.divider()

# --------------------------------------------------------------------------- #
# Section 2 — pricing
# --------------------------------------------------------------------------- #
st.subheader("Free-to-play wins reach; paid wins ratings")
left, right = st.columns(2)

with left:
    fig = px.histogram(
        view,
        x="review_score",
        color="price_type",
        color_discrete_map=se.PRICE_COLORS,
        category_orders={"price_type": se.PRICE_ORDER},
        nbins=24,
        barmode="overlay",
        histnorm="percent",
        opacity=0.7,
        labels={"review_score": "% positive reviews", "price_type": ""},
    )
    fig.update_layout(bargap=0.04, yaxis_title="% of titles in group")
    st.plotly_chart(styled(fig), width="stretch")
    st.caption(
        "Distribution of review scores, normalised within each group so the shapes "
        "compare fairly (paid titles outnumber free ones). Paid sits further right."
    )

with right:
    med = (
        view.groupby("price_type")["review_score"]
        .median()
        .reindex(se.PRICE_ORDER)
        .dropna()
        .reset_index()
    )
    fig = px.bar(
        med,
        x="review_score",
        y="price_type",
        orientation="h",
        color="price_type",
        color_discrete_map=se.PRICE_COLORS,
        text=med["review_score"].map(lambda v: f"{v:.0f}%"),
        labels={"review_score": "Median % positive", "price_type": ""},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, xaxis_range=[0, 100])
    st.plotly_chart(styled(fig), width="stretch")
    st.caption("Median review score by pricing.")

st.divider()

# --------------------------------------------------------------------------- #
# Section 3 — genres: common vs. loved
# --------------------------------------------------------------------------- #
st.subheader("The most *common* genre isn't the best-*rated* one")
left2, right2 = st.columns(2)

with left2:
    counts = view["primary_genre"].value_counts().head(12).reset_index()
    counts.columns = ["genre", "games"]
    fig = px.bar(
        counts,
        x="games",
        y="genre",
        orientation="h",
        text="games",
        labels={"games": "Number of games", "genre": ""},
    )
    fig.update_traces(marker_color=se.ACCENT, textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(styled(fig), width="stretch")
    st.caption("How big a genre is (by title count).")

with right2:
    eligible = view.groupby("primary_genre").filter(lambda g: len(g) >= 5)
    loved = (
        eligible.groupby("primary_genre")["rating_quality"]
        .median()
        .sort_values()
        .tail(10)
        .reset_index()
    )
    fig = px.bar(
        loved,
        x="rating_quality",
        y="primary_genre",
        orientation="h",
        text=loved["rating_quality"].map(lambda v: f"{v:.0f}%"),
        labels={"rating_quality": "Median reliable rating", "primary_genre": ""},
    )
    fig.update_traces(marker_color=se.ACCENT, textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_range=[0, 100])
    st.plotly_chart(styled(fig), width="stretch")
    st.caption("How *loved* a genre is (Wilson median, genres with ≥5 titles).")

st.divider()

# --------------------------------------------------------------------------- #
# Section 4 — leaderboard
# --------------------------------------------------------------------------- #
st.subheader("The leaderboard")
sort_by = st.radio(
    "Rank by",
    ["Most reliable rating", "Most owned"],
    horizontal=True,
    label_visibility="collapsed",
)
sort_col = "rating_quality" if sort_by == "Most reliable rating" else "owners_est"

table = (
    view.sort_values(sort_col, ascending=False)
    .head(20)
    .assign(owners_m=lambda d: d["owners_est"] / 1e6)[
        ["name", "primary_genre", "price_type", "review_score", "rating_quality", "reviews_total", "owners_m"]
    ]
    .rename(
        columns={
            "name": "Game",
            "primary_genre": "Genre",
            "price_type": "Pricing",
            "review_score": "Rating",
            "rating_quality": "Reliable rating",
            "reviews_total": "Reviews",
            "owners_m": "Est. owners (M)",
        }
    )
)

st.dataframe(
    table,
    width="stretch",
    hide_index=True,
    column_config={
        "Rating": st.column_config.NumberColumn(format="%.0f%%", help="Raw % positive reviews."),
        "Reliable rating": st.column_config.ProgressColumn(
            min_value=0, max_value=100, format="%.0f%%", help="Wilson lower-bound score."
        ),
        "Reviews": st.column_config.NumberColumn(format="%d"),
        "Est. owners (M)": st.column_config.NumberColumn(format="%.1f M"),
    },
)

st.download_button(
    "⬇ Download filtered data (CSV)",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="steam_games_filtered.csv",
    mime="text/csv",
)

st.caption(
    "Source: SteamSpy. Sample: the most-owned titles on Steam. Owner counts are banded ranges "
    "(midpoints shown), so review scores are the more reliable signal. Built with pandas, Plotly, and Streamlit."
)
