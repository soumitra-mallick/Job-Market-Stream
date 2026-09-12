"""
Internship Job Watch — Streamlit dashboard.

Reads live data from the already-deployed FastAPI analytics service
(job-market-stream.onrender.com) and renders the same panels as the
original D3/Chart.js index.html dashboard: pulse metrics, competition
heatmap, historical trends, recent activity, skills intelligence,
culture keywords, and a geographic job explorer.

No database credentials needed — the API is public (CORS: *) and does
the Postgres/Supabase querying for us.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
st.set_page_config(page_title="Internship Job Watch", layout="wide", page_icon="📊")

DEFAULT_API = "https://job-market-stream.onrender.com"
# Override by setting API_BASE in Streamlit Cloud secrets if you ever move
# the backend somewhere else.
API_BASE = st.secrets.get("API_BASE", DEFAULT_API)

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# --------------------------------------------------------------------------
# Theme — mirrors the dark gradient / glass-card look of the original page
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #020617 100%); }
    h1, h2, h3 { color: #f3f4f6 !important; }
    .iw-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #38bdf8, #a855f7);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .iw-subtitle { color: #9ca3af; margin-bottom: 1.5rem; }
    .pulse-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(168,85,247,0.12));
        border: 1px solid rgba(59,130,246,0.25);
        border-radius: 1rem; padding: 1.1rem 1.25rem; height: 100%;
    }
    .pulse-label { color: #9ca3af; font-size: 0.78rem; letter-spacing: 0.05em; text-transform: uppercase; }
    .pulse-value { font-size: 1.8rem; font-weight: 700; color: #f9fafb; margin: 0.25rem 0; }
    .pulse-change { color: #9ca3af; font-size: 0.85rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(15, 23, 42, 0.55); border-radius: 1rem;
        border: 1px solid rgba(59, 130, 246, 0.12);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e5e7eb",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
@st.cache_data(ttl=180, show_spinner=False)  # "Updated every 3 minutes"
def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001 - surfacing to the UI, not swallowing
        return {"__error__": str(e)}


def as_df(data) -> pd.DataFrame:
    if isinstance(data, dict) and "__error__" in data:
        return pd.DataFrame()
    if isinstance(data, dict):
        data = data.get("nodes", data)
    return pd.DataFrame(data)


def warn_if_error(data, label: str) -> bool:
    if isinstance(data, dict) and "__error__" in data:
        st.warning(
            f"Couldn't load {label}: {data['__error__']}. "
            "The API may be waking up from sleep (Render free tier) — try refreshing in ~30s."
        )
        return True
    return False


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown('<div class="iw-title">Internship Job Watch</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="iw-subtitle">Real-time insights powered by advanced analytics • '
    'Updated every 3 minutes</div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Pulse metrics
# --------------------------------------------------------------------------
pulse = api_get("/api/pulse_metrics")
top_skill_data = api_get("/api/trending_skills", {"days_back": 7, "top_n": 1})

c1, c2, c3, c4 = st.columns(4)
pulse_ok = not warn_if_error(pulse, "pulse metrics") and pulse

with c1:
    if pulse_ok:
        lh = pulse.get("last_hour", {})
        arrow = "▲" if lh.get("trend") == "up" else "▼" if lh.get("trend") == "down" else "→"
        st.markdown(
            f"""<div class="pulse-card">
                <div class="pulse-label">Last Hour</div>
                <div class="pulse-value">{lh.get('job_count', '--')}</div>
                <div class="pulse-change">{arrow} {lh.get('vs_weekly_avg', 0)}% vs weekly avg</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pulse-card">Loading…</div>', unsafe_allow_html=True)

with c2:
    if pulse_ok:
        d24 = pulse.get("last_24h", {})
        st.markdown(
            f"""<div class="pulse-card">
                <div class="pulse-label">Last 24 Hours</div>
                <div class="pulse-value">{d24.get('job_count', '--')}</div>
                <div class="pulse-change">📍 {d24.get('hottest_location', '--')}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pulse-card">Loading…</div>', unsafe_allow_html=True)

with c3:
    if pulse_ok:
        d24 = pulse.get("last_24h", {})
        st.markdown(
            f"""<div class="pulse-card">
                <div class="pulse-label">Hottest Function</div>
                <div class="pulse-value" style="font-size:1.2rem;">{d24.get('hottest_function', '--')}</div>
                <div class="pulse-change">Avg {d24.get('avg_applicants', '--')} applicants</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pulse-card">Loading…</div>', unsafe_allow_html=True)

with c4:
    trending_top = as_df(top_skill_data)
    top_skill = trending_top.iloc[0]["skill"] if not trending_top.empty else "--"
    st.markdown(
        f"""<div class="pulse-card">
            <div class="pulse-label">Trending Skill</div>
            <div class="pulse-value" style="font-size:1.2rem;">{top_skill}</div>
            <div class="pulse-change">Most mentioned this week</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.write("")

# --------------------------------------------------------------------------
# Competition heatmap
# --------------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Competition Heatmap — Best Times to Apply")
    st.caption("Darker green = fewer applicants (better chance). Darker red = more competition.")

    heat = as_df(api_get("/api/competition_heatmap", {"days": 30}))
    if not warn_if_error(heat, "competition heatmap") and not heat.empty:
        pivot = heat.pivot(index="day_of_week", columns="hour", values="avg_applicants")
        pivot = pivot.reindex(index=range(7), columns=range(24))
        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=[f"{h:02d}:00" for h in pivot.columns],
                y=[DAY_NAMES[d] for d in pivot.index],
                colorscale=[[0, "#166534"], [0.5, "#facc15"], [1, "#b91c1c"]],
                colorbar=dict(title="Avg\napplicants"),
                hovertemplate="%{y} %{x}<br>Avg applicants: %{z:.1f}<extra></extra>",
            )
        )
        fig.update_layout(**PLOTLY_LAYOUT, height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No heatmap data yet.")

st.write("")

# --------------------------------------------------------------------------
# Historical Trends (left) / Recent Activity (right)
# --------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.markdown("## Historical Trends")

    with st.container(border=True):
        st.subheader("Daily Job Postings")
        st.caption("180-day trend analysis")
        daily = as_df(api_get("/api/daily_counts", {"days": 180}))
        if not warn_if_error(daily, "daily postings") and not daily.empty:
            fig = px.line(daily, x="day", y="job_count", markers=True)
            fig.update_traces(line_color="#3b82f6")
            fig.update_layout(**PLOTLY_LAYOUT, height=260)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    with st.container(border=True):
        st.subheader("Remote Work Evolution")
        st.caption("Work mode distribution over time")
        remote = as_df(api_get("/api/remote_evolution", {"days": 180}))
        if not warn_if_error(remote, "remote work evolution") and not remote.empty:
            color_map = {}
            for mode in remote["work_mode"].unique():
                if "Remote" in mode:
                    color_map[mode] = "#22c55e"
                elif "Hybrid" in mode:
                    color_map[mode] = "#3b82f6"
                elif "site" in mode.lower():
                    color_map[mode] = "#ef4444"
                else:
                    color_map[mode] = "#6b7280"
            fig = px.area(remote, x="week", y="percentage", color="work_mode", color_discrete_map=color_map)
            fig.update_layout(**PLOTLY_LAYOUT, height=260, legend_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    with st.container(border=True):
        st.subheader("Job Function Distribution")
        st.caption("All-time breakdown by function")
        jf = as_df(api_get("/api/jobs_by_function"))
        if not warn_if_error(jf, "job function distribution") and not jf.empty:
            fig = px.pie(jf.head(10), names="job_function", values="count", hole=0.45)
            fig.update_layout(**PLOTLY_LAYOUT, height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

with right:
    st.markdown("## Recent Activity")

    with st.container(border=True):
        st.subheader("Company Hiring Velocity")
        st.caption("Top companies ramping up (last 30 days)")
        cv = as_df(api_get("/api/company_velocity", {"days": 30, "top_n": 10}))
        if not warn_if_error(cv, "company hiring velocity") and not cv.empty:
            fig = px.line(cv, x="day", y="cumulative_posts", color="company_name")
            fig.update_layout(**PLOTLY_LAYOUT, height=260, legend_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    with st.container(border=True):
        st.subheader("Job Lifecycle Funnel")
        st.caption("How long jobs stay active")
        life = as_df(api_get("/api/job_lifecycle"))
        if not warn_if_error(life, "job lifecycle") and not life.empty:
            palette = ["#22c55e", "#3b82f6", "#a855f7", "#f59e0b", "#ef4444", "#6b7280"]
            fig = go.Figure(
                go.Funnel(
                    y=life["lifecycle_stage"], x=life["job_count"],
                    marker=dict(color=palette[: len(life)]),
                )
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    with st.container(border=True):
        st.subheader("Last 24 Hours Activity")
        st.caption("Hourly job posting volume")
        hourly = as_df(api_get("/api/hourly_counts", {"hours": 24}))
        if not warn_if_error(hourly, "hourly activity") and not hourly.empty:
            fig = px.scatter(
                hourly, x="hour", y="job_count", size="job_count", color="job_count",
                color_continuous_scale=["#1e293b", "#3b82f6", "#a855f7"],
                size_max=40,
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=260, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

st.write("")

# --------------------------------------------------------------------------
# Skills Intelligence
# --------------------------------------------------------------------------
st.markdown("## Skills Intelligence")
colA, colB = st.columns(2)

with colA:
    with st.container(border=True):
        st.subheader("Skills Network")
        st.caption("Relative demand — box size = mention frequency")
        net = api_get("/api/skills_network", {"limit": 30})
        nodes = net.get("nodes", []) if isinstance(net, dict) else []
        if nodes:
            ndf = pd.DataFrame(nodes)
            fig = px.treemap(
                ndf, path=["label"], values="size",
                color="size", color_continuous_scale=["#1e293b", "#3b82f6", "#a855f7"],
            )
            fig.update_traces(textfont_color="white")
            fig.update_layout(**PLOTLY_LAYOUT, height=400, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skills data yet.")

with colB:
    with st.container(border=True):
        st.subheader("Trending Skills")
        st.caption("Biggest movers in the last 30 days")
        trend = as_df(api_get("/api/trending_skills", {"days_back": 30, "top_n": 12}))
        if not warn_if_error(trend, "trending skills") and not trend.empty:
            trend = trend.sort_values("change_percent")
            colors = [
                "#22c55e" if t == "growing" else "#ef4444" if t == "declining" else "#6b7280"
                for t in trend["trend"]
            ]
            fig = go.Figure(go.Bar(x=trend["change_percent"], y=trend["skill"], orientation="h", marker_color=colors))
            fig.update_layout(**PLOTLY_LAYOUT, height=400, xaxis_title="% change")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

# --------------------------------------------------------------------------
# Culture keywords
# --------------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Company Culture Keywords")
    st.caption("Most mentioned culture terms in job descriptions")
    culture = api_get("/api/culture_keywords", {"limit": 20})
    cdf = pd.DataFrame(culture) if isinstance(culture, list) else pd.DataFrame()
    if not cdf.empty:
        cdf = cdf.sort_values("count")
        fig = go.Figure(
            go.Bar(
                x=cdf["count"], y=cdf["keyword"], orientation="h", marker_color="#a855f7",
                text=cdf["percentage"].map(lambda p: f"{p}%"), textposition="outside",
            )
        )
        fig.update_layout(**PLOTLY_LAYOUT, height=max(300, 22 * len(cdf)))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No culture keyword data yet.")

st.write("")

# --------------------------------------------------------------------------
# Geographic Distribution & Job Explorer
# --------------------------------------------------------------------------
st.markdown("## Geographic Distribution & Job Explorer")
colM, colE = st.columns(2)

jobs_df = as_df(api_get("/api/map_jobs", {"limit": 2000, "hours": 24}))


def applicant_bucket(n):
    if n is None or pd.isna(n):
        return "Unknown"
    if n <= 60:
        return "Low"
    if n <= 100:
        return "Medium"
    return "High"


if not jobs_df.empty and "num_applicants" in jobs_df.columns:
    jobs_df["applicant_bucket"] = jobs_df["num_applicants"].apply(applicant_bucket)

with colM:
    with st.container(border=True):
        st.subheader("Job Locations Map")
        st.caption("Colors show applicant levels • Low ≤60 · Medium 61–100 · High 100+")
        mapdf = (
            jobs_df.dropna(subset=["latitude", "longitude"])
            if not jobs_df.empty and {"latitude", "longitude"}.issubset(jobs_df.columns)
            else pd.DataFrame()
        )
        if not mapdf.empty:
            color_map = {"Low": "#4A90E2", "Medium": "#F39C12", "High": "#27AE60", "Unknown": "#7f8c8d"}
            fig = px.scatter_mapbox(
                mapdf, lat="latitude", lon="longitude", color="applicant_bucket",
                color_discrete_map=color_map, hover_name="job_title",
                hover_data=["company_name", "location", "num_applicants"], zoom=2,
            )
            fig.update_layout(mapbox_style="carto-darkmatter", **PLOTLY_LAYOUT, height=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No geocoded jobs in the last 24 hours.")

with colE:
    with st.container(border=True):
        st.subheader("Interactive Job Explorer")
        st.caption("Filter by category and search")
        dim_map = {
            "Function": "Job Function",
            "Industry": "Industries",
            "Work Mode": "work_mode",
            "Degree": "degree_qualifications",
            "Visa Sponsorship": "visa_sponsorship",
        }
        if not jobs_df.empty:
            dim_label = st.selectbox("Group by", list(dim_map.keys()))
            dim_col = dim_map[dim_label]
            if dim_col in jobs_df.columns:
                counts = jobs_df[dim_col].fillna("Unknown").value_counts().head(15)
                fig = px.bar(x=counts.values, y=counts.index, orientation="h")
                fig.update_traces(marker_color="#3b82f6")
                fig.update_layout(**PLOTLY_LAYOUT, height=320, yaxis_title=None, xaxis_title="Jobs")
                st.plotly_chart(fig, use_container_width=True)

            query = st.text_input("Search job title or company")
            table = jobs_df
            if query and {"job_title", "company_name"}.issubset(jobs_df.columns):
                mask = jobs_df["job_title"].str.contains(query, case=False, na=False) | jobs_df[
                    "company_name"
                ].str.contains(query, case=False, na=False)
                table = jobs_df[mask]

            display_cols = [
                c for c in ["job_title", "company_name", "location", "work_mode", "num_applicants", "time_posted"]
                if c in table.columns
            ]
            st.dataframe(
                table[display_cols].rename(
                    columns={
                        "job_title": "Title", "company_name": "Company", "location": "Location",
                        "work_mode": "Mode", "num_applicants": "Applicants", "time_posted": "Posted",
                    }
                ),
                use_container_width=True,
                height=300,
            )
        else:
            st.info("No recent jobs to explore.")

st.caption(f"Data source: {API_BASE} • Cached for 3 minutes")
