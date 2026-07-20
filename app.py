#!/usr/bin/env python3
"""
CAPES Metrics — Journal & Conference Classifier
================================================
Desktop application (Streamlit) for browsing the QUALIS/CAPES classification
of scientific journals and conferences by research area.

Procedimento 2 — Área de Computação 2025–2028.

Data source: consolidated from the research group's curated spreadsheet
(percentile Scopus + computed estrato), cross-referenced with the official
QUALIS-NOVO CAPES list for reference.

Run locally:      streamlit run app.py
Export to static: see export_html.py (offline single-file build)
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIG & DATA
# ----------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "capes_data.json"

# Estrato ordering: A1 is the top of the scale, C the bottom.
ESTRATO_ORDER = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"]

# Each estrato gets its own colour. The A-band uses a warm gold-to-amber
# gradient (the "high-impact" band); the B-band cools toward slate so the
# visual hierarchy reads at a glance without needing the label.
ESTRATO_COLORS = {
    "A1": "#C8962B",   # deep gold
    "A2": "#D6A93E",
    "A3": "#E0BC5C",
    "A4": "#E8CE86",
    "B1": "#7E93A6",   # slate band
    "B2": "#8FA1B0",
    "B3": "#A3B1BC",
    "B4": "#B9C3CB",
    "C":  "#C9CDD2",
}


@st.cache_data
def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    rev = pd.DataFrame(raw["revistas"])
    conf = pd.DataFrame(raw["conferencias"])

    # Normalise area lists into a joined string for display + keep list for filtering
    rev["areas_str"] = rev["areas"].apply(lambda xs: ", ".join(xs))
    conf["areas_str"] = conf["areas"].apply(lambda xs: ", ".join(xs))

    return rev, conf, raw["areas"]


REVISTAS, CONFERENCIAS, AREAS = load_data()


# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------

def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --bg: #14171C;
            --panel: #1C2128;
            --panel-2: #232A33;
            --ink: #ECEEF1;
            --muted: #9AA3AD;
            --line: #2C333D;
            --gold: #D6A93E;
        }

        .stApp {
            background:
                radial-gradient(1200px 600px at 80% -10%, rgba(214,169,62,0.08), transparent 60%),
                var(--bg);
            color: var(--ink);
        }

        /* Hide default Streamlit chrome for a more "app" feel */
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}

        /* Masthead */
        .masthead {
            border-bottom: 1px solid var(--line);
            padding-bottom: 1.1rem;
            margin-bottom: 1.4rem;
        }
        .masthead .eyebrow {
            font-family: 'Inter', sans-serif;
            font-size: 0.72rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            color: var(--gold);
            font-weight: 600;
        }
        .masthead h1 {
            font-family: 'Fraunces', serif;
            font-weight: 900;
            font-size: 2.6rem;
            line-height: 1.02;
            margin: 0.25rem 0 0.15rem 0;
            color: var(--ink);
        }
        .masthead .sub {
            font-family: 'Inter', sans-serif;
            color: var(--muted);
            font-size: 0.95rem;
        }

        /* Stat strip */
        .stat-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 1rem 1.2rem;
            height: 100%;
        }
        .stat-card .num {
            font-family: 'Fraunces', serif;
            font-weight: 600;
            font-size: 1.9rem;
            color: var(--ink);
        }
        .stat-card .lbl {
            font-family: 'Inter', sans-serif;
            font-size: 0.74rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
        }

        /* Estrato badge */
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 0.78rem;
            color: #14171C;
        }

        /* Section heading */
        .sec-h {
            font-family: 'Fraunces', serif;
            font-weight: 600;
            font-size: 1.25rem;
            color: var(--ink);
            margin: 0.4rem 0 0.6rem 0;
        }

        /* Tabs restyle */
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 10px 10px 0 0;
            padding: 8px 18px;
            color: var(--muted);
        }
        .stTabs [aria-selected="true"] {
            background: var(--panel-2) !important;
            color: var(--gold) !important;
            border-bottom: 2px solid var(--gold) !important;
        }

        /* Dataframe tweaks */
        [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; }

        /* Inputs */
        .stTextInput input, .stMultiSelect div[data-baseweb="select"] > div {
            background: var(--panel) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }
        label, .stMarkdown p { color: var(--ink); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge_html(estrato):
    if not estrato:
        return ""
    color = ESTRATO_COLORS.get(estrato, "#C9CDD2")
    return f'<span class="badge" style="background:{color}">{estrato}</span>'


# ----------------------------------------------------------------------------
# CHARTS
# ----------------------------------------------------------------------------

def distribution_chart(df, title):
    """Horizontal stacked-by-estrato bar of the estrato distribution."""
    counts = df["estrato"].value_counts()
    cats = [e for e in ESTRATO_ORDER if e in counts.index]
    values = [int(counts[e]) for e in cats]
    colors = [ESTRATO_COLORS[e] for e in cats]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=cats,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=values,
            textposition="outside",
            textfont=dict(color="#ECEEF1", family="Inter", size=13),
            hovertemplate="%{y}: %{x} entries<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(family="Fraunces", size=16, color="#ECEEF1")),
        height=300,
        margin=dict(l=10, r=20, t=44, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(cats)),
            color="#9AA3AD",
            tickfont=dict(family="Inter", size=13),
        ),
        xaxis=dict(showgrid=True, gridcolor="#2C333D", color="#9AA3AD", zeroline=False),
        showlegend=False,
    )
    return fig


def area_chart(df, title):
    """Bar of entry count per research area."""
    exploded = df.explode("areas")
    counts = exploded["areas"].value_counts().sort_values(ascending=True)

    fig = go.Figure(
        go.Bar(
            x=counts.values,
            y=counts.index,
            orientation="h",
            marker=dict(color="#D6A93E", line=dict(width=0)),
            text=counts.values,
            textposition="outside",
            textfont=dict(color="#ECEEF1", family="Inter", size=12),
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(family="Fraunces", size=16, color="#ECEEF1")),
        height=360,
        margin=dict(l=10, r=24, t=44, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(color="#9AA3AD", tickfont=dict(family="Inter", size=12)),
        xaxis=dict(showgrid=True, gridcolor="#2C333D", color="#9AA3AD", zeroline=False),
        showlegend=False,
    )
    return fig


# ----------------------------------------------------------------------------
# FILTER + TABLE HELPERS
# ----------------------------------------------------------------------------

def apply_filters(df, query, areas_sel, estratos_sel):
    out = df.copy()
    if query:
        q = query.lower()
        terms = [t.strip() for t in q.split(",") if t.strip()]
        if terms:
            mask = pd.Series(False, index=out.index)
            search_cols = [c for c in ["name", "sigla", "issn", "areas_str"] if c in out.columns]
            for t in terms:
                term_mask = pd.Series(False, index=out.index)
                for c in search_cols:
                    term_mask = term_mask | out[c].fillna("").str.lower().str.contains(t, regex=False)
                mask = mask | term_mask
            out = out[mask]
    if areas_sel:
        out = out[out["areas"].apply(lambda xs: any(a in xs for a in areas_sel))]
    if estratos_sel:
        out = out[out["estrato"].isin(estratos_sel)]
    return out


def estrato_sort_key(series):
    rank = {e: i for i, e in enumerate(ESTRATO_ORDER)}
    return series.map(lambda e: rank.get(e, 99))


def style_estrato(df, estrato_col="Estrato"):
    """Return a pandas Styler that paints the estrato cell with its band colour."""
    def _cell(val):
        color = ESTRATO_COLORS.get(val, "")
        if not color:
            return ""
        return (
            f"background-color: {color}; color: #14171C; font-weight: 700; "
            f"text-align: center; border-radius: 6px;"
        )
    styler = df.style.map(_cell, subset=[estrato_col])
    styler = styler.set_properties(**{"font-size": "0.9rem"})
    return styler


# ----------------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------------

st.set_page_config(page_title="CAPES Metrics", page_icon="📊", layout="wide")
inject_css()

# --- Masthead ---
st.markdown(
    """
    <div class="masthead">
        <div class="eyebrow">Procedimento 2 · Computação 2025–2028</div>
        <h1>CAPES Metrics</h1>
        <div class="sub">QUALIS classification of scientific journals and conferences, by research area.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Stat strip ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-card"><div class="num">{len(REVISTAS)}</div>'
                f'<div class="lbl">Journals</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><div class="num">{len(CONFERENCIAS)}</div>'
                f'<div class="lbl">Conferences</div></div>', unsafe_allow_html=True)
with c3:
    n_areas = len(AREAS)
    st.markdown(f'<div class="stat-card"><div class="num">{n_areas}</div>'
                f'<div class="lbl">Research areas</div></div>', unsafe_allow_html=True)
with c4:
    a1 = int((REVISTAS["estrato"] == "A1").sum() + (CONFERENCIAS["estrato"] == "A1").sum())
    st.markdown(f'<div class="stat-card"><div class="num">{a1}</div>'
                f'<div class="lbl">A1 entries</div></div>', unsafe_allow_html=True)

st.write("")

tab_j, tab_c, tab_o = st.tabs(["  Journals  ", "  Conferences  ", "  Overview  "])

# ============================ JOURNALS ============================
with tab_j:
    f1, f2, f3 = st.columns([2, 1.5, 1.5])
    with f1:
        q = st.text_input("Search", placeholder="Name, ISSN or area — comma for multiple",
                          key="q_rev", label_visibility="collapsed")
    with f2:
        areas_sel = st.multiselect("Research area", AREAS, key="area_rev",
                                   placeholder="All areas", label_visibility="collapsed")
    with f3:
        estr_avail = [e for e in ESTRATO_ORDER if e in REVISTAS["estrato"].dropna().unique()]
        estr_sel = st.multiselect("Estrato", estr_avail, key="estr_rev",
                                  placeholder="All estratos", label_visibility="collapsed")

    filtered = apply_filters(REVISTAS, q, areas_sel, estr_sel)
    filtered = filtered.sort_values(
        by="estrato", key=estrato_sort_key, kind="stable"
    )

    st.caption(f"{len(filtered)} of {len(REVISTAS)} journals")

    show = filtered[["name", "issn", "percentile", "estrato", "areas_str", "scopus_url"]].copy()
    show.columns = ["Journal", "ISSN", "Percentile", "Estrato", "Areas", "Scopus"]

    st.dataframe(
        style_estrato(show),
        hide_index=True,
        use_container_width=True,
        height=520,
        column_config={
            "Journal": st.column_config.TextColumn(width="large"),
            "Percentile": st.column_config.NumberColumn(format="%d%%", width="small"),
            "Estrato": st.column_config.TextColumn(width="small"),
            "Scopus": st.column_config.LinkColumn("Scopus", display_text="open ↗", width="small"),
        },
    )

# ============================ CONFERENCES ============================
with tab_c:
    g1, g2, g3 = st.columns([2, 1.5, 1.5])
    with g1:
        qc = st.text_input("Search", placeholder="Name, acronym or area — comma for multiple",
                          key="q_conf", label_visibility="collapsed")
    with g2:
        areas_sel_c = st.multiselect("Research area", AREAS, key="area_conf",
                                     placeholder="All areas", label_visibility="collapsed")
    with g3:
        estr_avail_c = [e for e in ESTRATO_ORDER if e in CONFERENCIAS["estrato"].dropna().unique()]
        estr_sel_c = st.multiselect("Estrato", estr_avail_c, key="estr_conf",
                                    placeholder="All estratos", label_visibility="collapsed")

    filtered_c = apply_filters(CONFERENCIAS, qc, areas_sel_c, estr_sel_c)
    filtered_c = filtered_c.sort_values(by="estrato", key=estrato_sort_key, kind="stable")

    st.caption(f"{len(filtered_c)} of {len(CONFERENCIAS)} conferences")

    show_c = filtered_c[["sigla", "name", "estrato", "areas_str", "submission", "event_date"]].copy()
    show_c.columns = ["Acronym", "Conference", "Estrato", "Areas", "Submission", "Event"]

    st.dataframe(
        style_estrato(show_c),
        hide_index=True,
        use_container_width=True,
        height=520,
        column_config={
            "Acronym": st.column_config.TextColumn(width="small"),
            "Conference": st.column_config.TextColumn(width="large"),
            "Estrato": st.column_config.TextColumn(width="small"),
        },
    )

# ============================ OVERVIEW ============================
with tab_o:
    st.markdown('<div class="sec-h">Estrato distribution</div>', unsafe_allow_html=True)
    o1, o2 = st.columns(2)
    with o1:
        st.plotly_chart(distribution_chart(REVISTAS, "Journals by estrato"),
                        use_container_width=True)
    with o2:
        st.plotly_chart(distribution_chart(CONFERENCIAS, "Conferences by estrato"),
                        use_container_width=True)

    st.markdown('<div class="sec-h">Coverage by research area</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1:
        st.plotly_chart(area_chart(REVISTAS, "Journals per area"), use_container_width=True)
    with p2:
        st.plotly_chart(area_chart(CONFERENCIAS, "Conferences per area"), use_container_width=True)

    st.markdown('<div class="sec-h">How estratos are assigned</div>', unsafe_allow_html=True)
    st.markdown(
        """
        For **journals**, the estrato shown is the one computed from the Scopus
        highest-category percentile, following the CAPES Procedimento 2 bands
        (A1 ≥ 87.5%, A2 ≥ 75%, A3 ≥ 62.5%, A4 ≥ 50%, A5 ≥ 37.5%, A6 ≥ 25%,
        A7 ≥ 12.5%, A8 < 12.5%). For **conferences**, the estrato comes from the
        curated CE-SBC classification (H5-index based, with Top10/Top20 adjustment).
        """
    )
