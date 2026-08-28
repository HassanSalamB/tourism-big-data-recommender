"""Public portfolio and Streamlit UI for the Holiday Itinerary Data Platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

try:
    from src.api.dashboard_demo import WEATHER, demo_categories, demo_cities, demo_itinerary, demo_places, demo_summary
except ImportError:
    from dashboard_demo import WEATHER, demo_categories, demo_cities, demo_itinerary, demo_places, demo_summary

try:
    from src.api.service_registry import (
        backend_status_message,
        load_backend_status,
        load_service_registry,
        service_call_to_action,
    )
except ImportError:
    from service_registry import (
        backend_status_message,
        load_backend_status,
        load_service_registry,
        service_call_to_action,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = PROJECT_ROOT / "artifacts" / "screenshots"
ARCHITECTURE_HERO = PROJECT_ROOT / "docs" / "assets" / "holiday-platform-architecture.png"
LEVELS_OVERVIEW = PROJECT_ROOT / "docs" / "assets" / "holiday-platform-three-levels.png"
PROCESSING_ARCHITECTURE = PROJECT_ROOT / "docs" / "assets" / "level-2-spark-dbt-architecture.svg"
REPOSITORY_URL = "https://github.com/HassanSalamB/tourism-big-data-recommender"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PORTFOLIO_DEMO_MODE = os.getenv("PORTFOLIO_DEMO_MODE", "false").lower() in {"1", "true", "yes"}
BACKEND_STATUS = load_backend_status()
SERVICE_REGISTRY = load_service_registry()


st.set_page_config(page_title="Holiday Intelligence · Control Center", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
      :root {
        --ink:#edf9f5; --muted:#8ca9a5; --paper:#06131c; --line:#243b44;
        --green:#49d6aa; --mint:#71f7c5; --navy:#06131c; --warm:#f4b65d;
      }
      html {scroll-behavior:smooth;}
      [data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#f7faf9 0,#f2f6f5 100%);}
      [data-testid="stHeader"] {background:transparent;}
      .block-container {max-width:1220px; padding-top:1.4rem; padding-bottom:4rem;}
      [data-testid="stSidebar"] {border-right:0; background:linear-gradient(180deg,#071a22 0%,#0a292d 100%);}
      [data-testid="stSidebar"] * {color:#d9e8e5;}
      [data-testid="stSidebarNavSeparator"] {border-color:rgba(255,255,255,.1);}
      [data-testid="stSidebarNavItems"] {padding-top:.75rem;}
      [data-testid="stSidebarNavLink"] {border-radius:10px; margin:3px 8px; transition:background .16s ease,transform .16s ease;}
      [data-testid="stSidebarNavLink"]:hover {background:rgba(100,223,189,.1); transform:translateX(2px);}
      [data-testid="stSidebarNavLink"][aria-current="page"] {background:linear-gradient(90deg,rgba(100,223,189,.22),rgba(100,223,189,.08));}
      [data-testid="stSidebarNavLink"][aria-current="page"] * {color:#fff; font-weight:700;}
      [data-testid="stMetric"] {border:1px solid var(--line); border-radius:14px; padding:14px 16px; background:rgba(255,255,255,.84); box-shadow:0 8px 26px rgba(11,44,47,.05);}
      [data-testid="stPageLink-NavLink"], [data-testid^="stBaseLinkButton"], [data-testid="stBaseButton-primary"] {
        border-radius:11px !important; min-height:46px; font-weight:700; transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease;
      }
      [data-testid="stPageLink-NavLink"] {padding:0 14px; border:1px solid var(--line) !important; background:rgba(255,255,255,.86);}
      [data-testid="stPageLink-NavLink"]:hover, [data-testid^="stBaseLinkButton"]:hover, [data-testid="stBaseButton-primary"]:hover {
        transform:translateY(-1px); box-shadow:0 9px 22px rgba(10,60,57,.12); border-color:#8dcabc !important;
      }
      [data-testid="stImage"], [data-testid="stImageContainer"], [data-testid="stImage"] img {width:100% !important;}
      [data-testid="stImage"] img {height:auto !important; border-radius:14px;}
      [data-testid="stTabs"] [data-baseweb="tab-list"] {gap:7px;}
      [data-testid="stTabs"] [data-baseweb="tab"] {border-radius:10px 10px 0 0; padding:.5rem .9rem;}
      .portfolio-hero {position:relative; overflow:hidden; display:grid; grid-template-columns:minmax(0,1.45fr) minmax(260px,.65fr); gap:34px; padding:52px; border-radius:26px; color:#effaf7; background:radial-gradient(circle at 90% 4%,rgba(100,223,189,.24),transparent 30%),radial-gradient(circle at 3% 98%,rgba(47,120,167,.18),transparent 34%),linear-gradient(135deg,#061720 0%,#093a38 100%); box-shadow:0 24px 60px rgba(5,31,36,.18); margin:.15rem 0 1.1rem;}
      .portfolio-hero:after {content:""; position:absolute; width:330px; height:330px; border:1px solid rgba(255,255,255,.08); border-radius:50%; right:-155px; bottom:-220px;}
      .hero-copy,.hero-panel {position:relative; z-index:1;}
      .brand-row {display:flex; align-items:center; gap:10px; margin-bottom:22px;}
      .brand-mark {display:grid; place-items:center; width:35px; height:35px; border-radius:11px; color:#06221f; background:var(--mint); font-weight:900;}
      .brand-name {font-size:.77rem; color:#b8d4ce; font-weight:800; letter-spacing:.13em; text-transform:uppercase;}
      .live-pill {display:inline-flex; align-items:center; gap:7px; border:1px solid rgba(115,231,199,.33); border-radius:999px; padding:6px 10px; color:#baf1e2; background:rgba(58,157,133,.14); font-size:.72rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase;}
      .live-dot {width:7px; height:7px; border-radius:50%; background:#63e5bd; box-shadow:0 0 0 5px rgba(99,229,189,.11);}
      .portfolio-hero h1 {max-width:760px; color:white; font-size:clamp(2.35rem,4.4vw,4.35rem); line-height:.98; letter-spacing:-.055em; margin:0 0 20px;}
      .portfolio-hero .hero-lead {max-width:710px; color:#c3d8d4; font-size:1.08rem; line-height:1.65; margin:0;}
      .hero-actions {display:flex; flex-wrap:wrap; gap:11px; margin-top:28px;}
      .hero-actions a {display:inline-flex; align-items:center; justify-content:center; gap:9px; min-height:48px; padding:0 18px; border-radius:11px; text-decoration:none !important; font-weight:800; transition:transform .16s ease,box-shadow .16s ease;}
      .hero-actions a:hover {transform:translateY(-2px);}
      .cta-primary {color:#06221f !important; background:#6be0bf; box-shadow:0 12px 28px rgba(52,200,163,.2);}
      .cta-secondary {color:#ecf8f5 !important; border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.06);}
      .hero-panel {align-self:stretch; padding:22px; border:1px solid rgba(255,255,255,.12); border-radius:18px; background:rgba(4,21,27,.42); backdrop-filter:blur(8px);}
      .hero-panel small {color:#7ae0c4; font-weight:800; letter-spacing:.12em; text-transform:uppercase;}
      .signal {display:grid; grid-template-columns:31px 1fr; gap:11px; align-items:start; padding:15px 0; border-bottom:1px solid rgba(255,255,255,.09);}
      .signal:last-child {border-bottom:0; padding-bottom:0;}
      .signal-index {display:grid; place-items:center; width:28px; height:28px; border-radius:9px; color:#9debd6; background:rgba(100,223,189,.12); font-size:.72rem; font-weight:900;}
      .signal strong {display:block; color:#fff; font-size:.93rem; margin-bottom:2px;}
      .signal span {color:#9db9b4; font-size:.79rem; line-height:1.35;}
      .command-strip {display:grid; grid-template-columns:repeat(4,1fr); gap:1px; overflow:hidden; margin:0 0 2.7rem; border:1px solid var(--line); border-radius:15px; background:var(--line); box-shadow:0 12px 32px rgba(12,42,45,.05);}
      .command-cell {background:rgba(255,255,255,.9); padding:16px 18px;}
      .command-cell span {display:block; color:#72827f; font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase;}
      .command-cell strong {display:block; color:#143c39; font-size:1rem; margin-top:.22rem;}
      .section-heading {display:grid; grid-template-columns:minmax(0,.75fr) minmax(280px,.55fr); gap:34px; align-items:end; margin:2.75rem 0 1.15rem;}
      .section-kicker,.eyebrow {font-size:.72rem; color:#07856a; font-weight:900; letter-spacing:.15em; text-transform:uppercase; margin-bottom:.42rem;}
      .section-heading h2 {color:var(--ink); font-size:clamp(1.75rem,2.6vw,2.55rem); letter-spacing:-.035em; line-height:1.08; margin:0;}
      .section-heading p,.section-lead {color:var(--muted); font-size:.95rem; line-height:1.6; margin:0;}
      .architecture-shell {padding:12px; border:1px solid #ccdbd7; border-radius:19px; background:linear-gradient(145deg,#fff,#eef4f2); box-shadow:0 18px 45px rgba(10,44,46,.09);}
      .architecture-caption {display:flex; justify-content:space-between; gap:18px; align-items:center; color:#62726f; font-size:.86rem; line-height:1.5; margin:.75rem .25rem 0;}
      .architecture-caption strong {color:#123e39; white-space:nowrap;}
      .level-card,.card {min-height:148px; padding:21px; border:1px solid var(--line); border-radius:16px; background:rgba(255,255,255,.86); box-shadow:0 10px 28px rgba(9,48,47,.05);}
      .level-card small {color:#0a826b; font-weight:900; letter-spacing:.11em;}
      .level-card h3,.card h3 {color:#123d3a; font-size:1.05rem; margin:.55rem 0 .38rem;}
      .level-card p,.card p {color:#5f716e; font-size:.88rem; line-height:1.52; margin:0;}
      .stage-grid {display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:1rem;}
      .stage {position:relative; min-height:188px; padding:22px; border:1px solid var(--line); border-radius:17px; background:rgba(255,255,255,.82); overflow:hidden;}
      .stage:before {content:""; position:absolute; width:60px; height:3px; top:0; left:22px; background:linear-gradient(90deg,#19a984,#8ce1ca); border-radius:0 0 5px 5px;}
      .stage-number {display:inline-block; color:#087862; font-size:.68rem; font-weight:900; letter-spacing:.11em;}
      .stage h3 {font-size:1.04rem; color:#103b38; margin:.9rem 0 .5rem;}
      .stage p {font-size:.87rem; line-height:1.55; color:#5c706c; margin:0;}
      .reviewer-note {display:grid; grid-template-columns:170px 1fr; gap:22px; padding:22px 24px; border:1px solid #b9ded3; border-radius:16px; background:linear-gradient(120deg,#eaf8f4,#f7fbfa); margin:1.1rem 0 1.4rem; color:#244d47;}
      .reviewer-note strong {color:#123d38;}
      .evidence-marker {height:0; overflow:hidden;}
      .stElementContainer:has(.evidence-marker) + .stElementContainer [data-testid="stImage"] img {height:128px !important; object-fit:cover; object-position:top center;}
      .evidence-card {padding:10px 4px 4px;}
      .evidence-card h3 {min-height:42px; font-size:1rem; color:#123b38; margin:.35rem 0 .18rem;}
      .evidence-card p {min-height:76px; color:#667572; font-size:.82rem; line-height:1.45; margin:0 0 .45rem;}
      .page-hero {padding:30px 34px; margin:0 0 1rem; border:1px solid #cfe0dc; border-radius:20px; background:radial-gradient(circle at 95% 0,rgba(100,223,189,.15),transparent 32%),#fff; box-shadow:0 14px 38px rgba(10,44,46,.07);}
      .page-hero h1 {color:var(--ink); font-size:clamp(2rem,3vw,3rem); letter-spacing:-.045em; line-height:1.05; margin:.25rem 0 .55rem;}
      .page-hero p {max-width:820px; color:var(--muted); line-height:1.58; margin:0;}
      .page-badge {display:inline-flex; margin-top:14px; padding:6px 10px; border-radius:999px; color:#08745f; background:#e4f6f0; font-size:.7rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase;}
      .notice,.live-note {padding:13px 17px; border-radius:12px; margin:.5rem 0 1rem;}
      .notice {background:#fff7e5; border:1px solid #ead49c;}
      .live-note {background:#eaf7f3; border:1px solid #aed9cd;}
      .place-panel {border:1px solid #d8e1df; border-radius:12px; padding:.85rem 1rem; margin-bottom:.75rem; background:#fff; box-shadow:0 7px 18px rgba(10,44,46,.04);}
      .muted {color:#667875; font-size:.9rem;}
      .flow {padding:17px; border-radius:14px; background:linear-gradient(120deg,#092029,#0b3b3a); color:#eaf5f2; line-height:1.8; text-align:center; margin:1rem 0; box-shadow:0 10px 26px rgba(5,31,36,.1);}
      .flow strong {color:#69d5b9;}

      /* Product dashboard visual system */
      [data-testid="stAppViewContainer"] {background:radial-gradient(circle at 88% 0,rgba(42,132,123,.13),transparent 28%),linear-gradient(180deg,#06131c 0,#081821 100%); color:#e9f7f3;}
      [data-testid="stHeader"] {background:#06131cdd; border-bottom:1px solid rgba(255,255,255,.05);}
      .block-container {max-width:1380px; padding-top:1.1rem;}
      [data-testid="stSidebar"] {border-right:1px solid #20333b; background:linear-gradient(180deg,#07131a 0%,#0a2229 100%);}
      [data-testid="stMetric"] {border:1px solid #243b44; border-radius:12px; background:#0b1d27; box-shadow:0 12px 28px rgba(0,0,0,.16);}
      [data-testid="stMetricLabel"] {color:#789793;}
      [data-testid="stMetricValue"] {color:#f2fffb;}
      [data-testid="stVerticalBlockBorderWrapper"] {border-color:#243b44 !important; background:rgba(11,29,39,.78); border-radius:15px;}
      [data-testid="stPageLink-NavLink"] {border-color:#243b44 !important; background:#0b1d27; color:#dcece8;}
      .portfolio-hero {grid-template-columns:minmax(0,1.3fr) minmax(320px,.7fr); padding:38px 42px; border:1px solid #294750; border-radius:18px; background:radial-gradient(circle at 90% 4%,rgba(113,247,197,.19),transparent 31%),linear-gradient(135deg,#081922 0%,#0b3032 100%); box-shadow:0 24px 60px rgba(0,0,0,.28);}
      .brand-mark {width:38px; height:38px; border:1px solid #71f7c5; border-radius:0; color:#71f7c5; background:#0a1b23; font:900 .76rem ui-monospace,monospace; letter-spacing:.06em;}
      .portfolio-hero h1 {font-size:clamp(2.5rem,4vw,4rem);}
      .command-strip {margin-bottom:2rem; border-color:#243b44; background:#243b44; box-shadow:0 12px 32px rgba(0,0,0,.16);}
      .command-cell {background:#0b1d27; padding:17px 18px;}
      .command-cell span {color:#668682;}
      .command-cell strong {color:#f0fbf7; font-size:1.05rem;}
      .command-cell strong em {color:#71f7c5; font-style:normal;}
      .section-heading h2,.page-hero h1 {color:#edf9f5;}
      .section-heading p,.section-lead,.page-hero p {color:#8ca9a5;}
      .architecture-shell,.level-card,.card,.stage {border-color:#243b44; background:#0b1d27; box-shadow:0 14px 32px rgba(0,0,0,.14);}
      .level-card h3,.card h3,.stage h3,.evidence-card h3 {color:#edf9f5;}
      .level-card p,.card p,.stage p,.evidence-card p {color:#8ca9a5;}
      .reviewer-note {border-color:#275047; background:linear-gradient(120deg,#0b2929,#0b2028); color:#a9c2bd;}
      .reviewer-note strong {color:#e9faf5;}
      .page-hero {border-color:#243b44; border-radius:16px; background:radial-gradient(circle at 95% 0,rgba(113,247,197,.13),transparent 32%),#0b1d27; box-shadow:0 14px 38px rgba(0,0,0,.16);}
      .notice {color:#e8d5a8; background:#2a2417; border-color:#66532c;}
      .live-note {color:#bce8db; background:#0c2a28; border-color:#27534b;}
      .place-panel {border-color:#243b44; background:#0d222c; box-shadow:0 7px 18px rgba(0,0,0,.12);}
      .muted {color:#8ca9a5;}
      .dashboard-panel {min-height:290px; padding:22px; border:1px solid #243b44; border-radius:14px; background:#0b1d27; box-shadow:0 14px 32px rgba(0,0,0,.16);}
      .panel-label {color:#71f7c5; font:800 .65rem ui-monospace,monospace; letter-spacing:.12em; text-transform:uppercase;}
      .dashboard-panel h3 {color:#f1fcf8; margin:.65rem 0 1.1rem; font-size:1.2rem;}
      .system-row {display:grid; grid-template-columns:12px 1fr auto; gap:10px; align-items:center; padding:12px 0; border-top:1px solid #243b44; color:#b8cdc8; font-size:.83rem;}
      .system-row i {width:7px; height:7px; border-radius:50%; background:#71f7c5; box-shadow:0 0 9px rgba(113,247,197,.7);}
      .system-row strong {color:#edf9f5; font:800 .65rem ui-monospace,monospace; text-transform:uppercase;}
      .sidebar-brand-card {margin:.2rem .45rem 1rem; padding:1rem; border:1px solid #294049; background:#0a1d25;}
      .sidebar-brand-card strong {display:block; color:#f3fcf9; font-size:.9rem;}
      .sidebar-brand-card span {display:block; margin-top:.28rem; color:#6f918d; font:700 .6rem ui-monospace,monospace; letter-spacing:.1em; text-transform:uppercase;}
      @media (max-width:900px) {
        .portfolio-hero {grid-template-columns:1fr; padding:38px;}
        .hero-panel {display:grid; grid-template-columns:repeat(3,1fr); gap:12px;}
        .hero-panel > small {grid-column:1/-1;}
        .signal {border-bottom:0; padding:8px 0;}
        .section-heading {grid-template-columns:1fr; gap:9px;}
        .stage-grid {grid-template-columns:repeat(2,1fr);}
      }
      @media (max-width:640px) {
        .block-container {padding-top:.8rem;}
        .portfolio-hero {padding:28px 22px; border-radius:20px; gap:24px;}
        .portfolio-hero h1 {font-size:2.35rem;}
        .portfolio-hero .hero-lead {font-size:.98rem;}
        .hero-panel {display:block;}
        .signal {border-bottom:1px solid rgba(255,255,255,.09); padding:13px 0;}
        .command-strip,.stage-grid {grid-template-columns:repeat(2,1fr);}
        .section-heading {margin-top:2.2rem;}
        .architecture-caption,.reviewer-note {display:block;}
        .architecture-caption strong {display:block; margin-bottom:4px;}
        .reviewer-note .eyebrow {margin-bottom:8px;}
        .page-hero {padding:24px 21px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, **params) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def platform_data() -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if PORTFOLIO_DEMO_MODE:
        return demo_summary(), demo_cities(), demo_categories()
    return api_get("/summary"), api_get("/cities", limit=100), api_get("/categories", limit=300)


def mode_notice() -> None:
    if PORTFOLIO_DEMO_MODE:
        st.markdown(
            '<div class="live-note"><strong>Interactive portfolio dataset.</strong> This hosted experience uses a curated sample; verified full-stack evidence remains available throughout the system pages.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="live-note"><strong>Full-stack mode.</strong> Connected to the FastAPI service at <code>{API_BASE_URL}</code>.</div>',
            unsafe_allow_html=True,
        )


def backend_status_notice() -> None:
    css_class, heading, message = backend_status_message(BACKEND_STATUS)
    st.markdown(
        f'<div class="{css_class}"><strong>{heading}.</strong> {message}</div>',
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, description: str, badge: str | None = None) -> None:
    badge_html = f'<span class="page-badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="page-hero">
          <div class="eyebrow">{kicker}</div>
          <h1>{title}</h1>
          <p>{description}</p>
          {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
          <div><div class="section-kicker">{kicker}</div><h2>{title}</h2></div>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def home_page() -> None:
    try:
        summary, cities, _ = platform_data()
    except requests.RequestException:
        summary, cities = demo_summary(), demo_cities()

    st.markdown(
        """
        <div class="portfolio-hero">
          <div class="hero-copy">
            <div class="brand-row">
              <span class="brand-mark">HI</span>
              <span class="brand-name">Holiday Intelligence</span>
              <span class="live-pill"><span class="live-dot"></span>System online</span>
            </div>
            <h1>Holiday Intelligence Control Center.</h1>
            <p class="hero-lead">Explore destinations, generate preference-aware itineraries and inspect the production-grade data platform powering every recommendation.</p>
            <div class="hero-actions">
              <a class="cta-primary" href="/itinerary_page" target="_self">Launch itinerary planner <span>→</span></a>
              <a class="cta-secondary" href="/architecture_page" target="_self">View system design</a>
            </div>
          </div>
          <aside class="hero-panel">
            <small>Platform status</small>
            <div class="signal"><span class="signal-index">01</span><div><strong>Destination index ready</strong><span>Curated points of interest across France</span></div></div>
            <div class="signal"><span class="signal-index">02</span><div><strong>Recommendation engine ready</strong><span>Preference, weather and graph context</span></div></div>
            <div class="signal"><span class="signal-index">03</span><div><strong>Observability connected</strong><span>Pipeline health and product quality signals</span></div></div>
          </aside>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="command-strip">
          <div class="command-cell"><span>Places indexed</span><strong><em>{summary['places']:,}</em></strong></div>
          <div class="command-cell"><span>Destinations</span><strong>{summary['cities']:,} cities</strong></div>
          <div class="command-cell"><span>Decision layer</span><strong>{summary['clusters']:,} Gold clusters</strong></div>
          <div class="command-cell"><span>Runtime</span><strong><em>Live</em> on Render</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_heading(
        "Live data surface",
        "Destination intelligence at a glance",
        "A populated operational view replaces the empty landing experience: inspect coverage now, then open the planner to build a complete trip.",
    )
    coverage, readiness = st.columns([0.64, 0.36], gap="large")
    with coverage:
        with st.container(border=True):
            st.markdown('<div class="panel-label">Destination coverage · top cities</div>', unsafe_allow_html=True)
            coverage_frame = pd.DataFrame(cities).nlargest(8, "poi_count")
            st.bar_chart(coverage_frame.set_index("city")["poi_count"], color="#71f7c5")
    with readiness:
        st.markdown(
            """
            <div class="dashboard-panel">
              <div class="panel-label">System readiness</div>
              <h3>Decision platform</h3>
              <div class="system-row"><i></i><span>Curated tourism dataset</span><strong>Ready</strong></div>
              <div class="system-row"><i></i><span>Preference-aware planner</span><strong>Ready</strong></div>
              <div class="system-row"><i></i><span>Weather context</span><strong>Live</strong></div>
              <div class="system-row"><i></i><span>Engineering evidence</span><strong>Verified</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    section_heading(
        "System architecture",
        "One platform, from raw feed to monitored product",
        "The overview connects orchestration, medallion storage, Spark processing, graph enrichment, serving, events and observability. Open the detailed view for the dbt branch and level-by-level design.",
    )
    with st.container(border=True):
        st.image(str(ARCHITECTURE_HERO), width="stretch")
        st.markdown(
            '<div class="architecture-caption"><strong>End-to-end system topology</strong><span>Airflow · PostgreSQL · Spark · dbt · Neo4j · FastAPI · Kafka · Prometheus · Grafana</span></div>',
            unsafe_allow_html=True,
        )
    architecture_actions = st.columns([1, 1, 1])
    with architecture_actions[0]:
        st.page_link(ARCHITECTURE_PAGE, label="Explore architecture levels", icon="🧱", width="stretch")
    with architecture_actions[1]:
        st.page_link(PIPELINE_PAGE, label="See pipeline evidence", icon="🔄", width="stretch")
    with architecture_actions[2]:
        st.page_link(OBSERVABILITY_PAGE, label="Review observability", icon="📊", width="stretch")

    section_heading(
        "Data-to-decision flow",
        "Four stages, one governed path",
        "Each stage has a clear engineering responsibility: capture change, create trust, produce intelligence, and measure whether the product remains useful.",
    )
    stage_content = [
        ("01 · INGEST", "Capture change", "Airflow ingests DATAtourisme archives and SHA-256 change detection prevents unnecessary reprocessing."),
        ("02 · TRUST", "Build governed layers", "Bronze preserves raw JSONB; Silver normalizes entities; Gold creates H3 and city-level analytical features."),
        ("03 · DECIDE", "Generate intelligence", "PostgreSQL, KMeans, weather and Neo4j relationships produce explainable destination recommendations."),
        ("04 · LEARN", "Observe outcomes", "Kafka events and Prometheus metrics expose usage, latency, category match, route distance and weather suitability."),
    ]
    stages_html = "".join(
        f'<div class="stage"><span class="stage-number">{number}</span><h3>{heading}</h3><p>{description}</p></div>'
        for number, heading, description in stage_content
    )
    st.markdown(f'<div class="stage-grid">{stages_html}</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="reviewer-note">
          <div class="eyebrow">Reviewer context</div>
          <div><strong>Why this is relevant to accommodation intelligence:</strong> the platform demonstrates the same engineering pattern—combine fragmented market signals, create governed features, serve explainable recommendations, and monitor whether the product is useful. The demonstration uses public tourism-supply data rather than proprietary hotel pricing or demand data.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_heading(
        "Explore the build",
        "Start with the product. Go deeper into the proof.",
        "The Streamlit product is live on Render. Engineering pages use recorded evidence from verified full-stack runs until the dedicated backend environment is online.",
    )
    cols = st.columns(4)
    with cols[0]:
        with st.container(border=True):
            st.markdown('<div class="evidence-marker"></div>', unsafe_allow_html=True)
            st.image(str(SCREENSHOTS / "01-streamlit-dashboard.png"), width="stretch")
            st.markdown('<div class="evidence-card"><h3>Live itinerary product</h3><p>Plan destination days, filter interests and inspect places on an interactive map.</p></div>', unsafe_allow_html=True)
            st.page_link(APP_PAGE, label="Open product", icon="🧭", width="stretch")
    with cols[1]:
        with st.container(border=True):
            st.markdown('<div class="evidence-marker"></div>', unsafe_allow_html=True)
            st.image(str(SCREENSHOTS / "03-airflow-dag-grid.png"), width="stretch")
            st.markdown('<div class="evidence-card"><h3>Pipeline & storage</h3><p>Inspect Airflow, medallion layers, Spark, dbt and Postgres execution evidence.</p></div>', unsafe_allow_html=True)
            st.page_link(PIPELINE_PAGE, label="Open pipeline", icon="🔄", width="stretch")
    with cols[2]:
        with st.container(border=True):
            st.markdown('<div class="evidence-marker"></div>', unsafe_allow_html=True)
            st.image(str(SCREENSHOTS / "02-fastapi-docs.png"), width="stretch")
            st.markdown('<div class="evidence-card"><h3>Serving & events</h3><p>Follow the request through FastAPI, Neo4j enrichment and Kafka events.</p></div>', unsafe_allow_html=True)
            st.page_link(SERVING_PAGE, label="Open serving", icon="🔌", width="stretch")
    with cols[3]:
        with st.container(border=True):
            st.markdown('<div class="evidence-marker"></div>', unsafe_allow_html=True)
            st.image(str(SCREENSHOTS / "11-grafana-kpis.png"), width="stretch")
            st.markdown('<div class="evidence-card"><h3>Observability</h3><p>Review service health, latency and product-quality metrics in Grafana.</p></div>', unsafe_allow_html=True)
            st.page_link(OBSERVABILITY_PAGE, label="Open metrics", icon="📊", width="stretch")


def architecture_page() -> None:
    page_header(
        "Platform blueprint",
        "Architecture details",
        "A reviewer-focused view of the request path, governed processing layers, Spark and dbt responsibilities, and the operational validation route.",
        "Recorded full-stack evidence",
    )
    backend_status_notice()

    section_heading(
        "System topology",
        "The complete platform at a glance",
        "The user-facing product is connected to the data platform, asynchronous event path and operational evidence behind it.",
    )
    with st.container(border=True):
        st.image(str(ARCHITECTURE_HERO), width="stretch")

    overview_tab, processing_tab, validation_tab = st.tabs(["Architecture levels", "Spark + dbt layer", "Reviewer path"])

    with overview_tab:
        st.subheader("Three engineering levels")
        st.markdown(
            '<p class="section-lead">Level 1 serves the product, Level 2 builds governed decision features, and Level 3 measures reliability and product quality.</p>',
            unsafe_allow_html=True,
        )
        st.image(str(LEVELS_OVERVIEW), width="stretch")
        level_columns = st.columns(3)
        level_content = [
            ("LEVEL 1", "Request serving", "Streamlit captures intent; FastAPI combines PostgreSQL, runtime clustering and Neo4j context."),
            ("LEVEL 2", "Processing & analytics", "Airflow governs incremental ETL while Spark and dbt build complementary decision features."),
            ("LEVEL 3", "Observability", "Prometheus, Grafana and Alertmanager track both service health and product usefulness."),
        ]
        for column, (level, heading, description) in zip(level_columns, level_content):
            with column:
                st.markdown(f'<div class="level-card"><small>{level}</small><h3>{heading}</h3><p>{description}</p></div>', unsafe_allow_html=True)

    with processing_tab:
        st.subheader("Level 2: Spark + dbt")
        st.markdown(
            '<p class="section-lead">Spark and dbt are not duplicate tools: Spark performs scalable feature computation over trusted snapshots; dbt produces tested SQL marts and explicit analytical contracts.</p>',
            unsafe_allow_html=True,
        )
        st.image(str(PROCESSING_ARCHITECTURE), width="stretch")
        spark_col, dbt_col = st.columns(2)
        with spark_col:
            st.markdown('<div class="card"><h3>Apache Spark</h3><p>Computes destination and city-level features from trusted Silver data, then writes analytical snapshots for downstream models and marts.</p></div>', unsafe_allow_html=True)
        with dbt_col:
            st.markdown('<div class="card"><h3>dbt</h3><p>Turns warehouse tables into tested marts with documented contracts, making Gold outputs easier to validate and reuse.</p></div>', unsafe_allow_html=True)

    with validation_tab:
        st.subheader("Recommended reviewer path")
        st.write("Start with the live itinerary app, then inspect the evidence pages that map each product capability to the backend implementation.")
        path_cols = st.columns(4)
        with path_cols[0]:
            st.page_link(APP_PAGE, label="Live demo", icon="🧭", width="stretch")
        with path_cols[1]:
            st.page_link(PIPELINE_PAGE, label="Pipeline evidence", icon="🔄", width="stretch")
        with path_cols[2]:
            st.page_link(SERVING_PAGE, label="Serving evidence", icon="🔌", width="stretch")
        with path_cols[3]:
            st.page_link(OBSERVABILITY_PAGE, label="Observability", icon="📊", width="stretch")


def itinerary_page() -> None:
    page_header(
        "Live product",
        "Build a destination itinerary",
        "Choose a city, trip length and interests. The product combines trusted place data, weather context and preference-aware recommendations into an explorable plan.",
        "Interactive on Render",
    )
    mode_notice()
    try:
        summary, cities, categories = platform_data()
    except requests.RequestException as exc:
        st.error(f"FastAPI is not reachable at {API_BASE_URL}.")
        st.exception(exc)
        st.stop()

    metric_cols = st.columns(5)
    metric_cols[0].metric("Places indexed", f"{summary['places']:,}")
    metric_cols[1].metric("Destinations", f"{summary['cities']:,}")
    metric_cols[2].metric("Popular cities", f"{summary['popular_destinations']:,}")
    metric_cols[3].metric("Categories", f"{summary['categories']:,}")
    metric_cols[4].metric("Gold clusters", f"{summary['clusters']:,}")

    left, right = st.columns([0.32, 0.68], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-label">Trip controls</div>', unsafe_allow_html=True)
            st.subheader("Plan your route")
            city_options = [item["city"] for item in cities]
            city = st.selectbox("Destination", options=city_options)
            days = st.slider("Days", 1, 5, 2)
            max_places = st.slider("Places per day", 1, 6, 3)
            selected_categories = st.multiselect("Interests", options=categories, placeholder="All categories")
            generate = st.button("Refresh itinerary", type="primary", width="stretch")

            try:
                weather = WEATHER[city] if PORTFOLIO_DEMO_MODE else api_get("/weather/current", city=city)
                weather_cols = st.columns(2)
                weather_cols[0].metric("Temperature", f"{weather['temperature_2m']:.1f} °C")
                weather_cols[1].metric("Wind", f"{weather['wind_speed_10m']:.1f} km/h")
                st.caption(f"Weather: {weather.get('observed_at', 'latest observation')}")
            except (requests.RequestException, KeyError):
                st.caption("Weather is currently unavailable.")

    with right:
        with st.container(border=True):
            st.markdown('<div class="panel-label">Workspace</div>', unsafe_allow_html=True)
            view = st.segmented_control("View", ["Itinerary", "Map & places", "Destinations"], default="Itinerary", label_visibility="collapsed")
        if view == "Itinerary":
            if PORTFOLIO_DEMO_MODE or generate:
                if PORTFOLIO_DEMO_MODE:
                    itinerary = demo_itinerary(city, days, max_places, selected_categories)
                else:
                    itinerary = api_post("/generate-itinerary", {"city": city, "days": days, "max_places_per_day": max_places, "categories": selected_categories})
                for day in itinerary:
                    st.markdown(f"### Day {day['day']}")
                    if not day["places"]:
                        st.caption("No additional places are available for this day in the selected sample.")
                    day_frame = pd.DataFrame(day["places"])
                    if not day_frame.empty:
                        st.caption(f"Day {day['day']} route map · zoom or open fullscreen to explore")
                        st.map(day_frame.rename(columns={"lat": "latitude", "lon": "longitude"}))
                    for place in day["places"]:
                        st.markdown(
                            f'<div class="place-panel"><strong>{place["start_time"]}–{place["end_time"]} · {place["name"]}</strong><div class="muted">{", ".join(place["categories"][:3])}</div><div>{place.get("address", "")}</div><div class="muted">Related: {", ".join(place["recommendations"])}</div></div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info("Choose a destination and generate an itinerary.")
        elif view == "Map & places":
            places = demo_places(city, selected_categories) if PORTFOLIO_DEMO_MODE else api_get("/places", city=city, limit=50, categories=selected_categories or None)
            frame = pd.DataFrame(places)
            if frame.empty:
                st.info("No places match the selected filters.")
            else:
                st.subheader(f"Explore {city} on the map")
                st.caption("Zoom, pan, or open fullscreen; the table below provides the corresponding place details.")
                st.map(frame.rename(columns={"lat": "latitude", "lon": "longitude"}))
                st.dataframe(frame[["name", "city", "address", "categories", "website"]], width="stretch", hide_index=True)
        else:
            city_frame = pd.DataFrame(cities)
            st.bar_chart(city_frame.set_index("city")["poi_count"], color="#71f7c5")
            st.dataframe(city_frame, width="stretch", hide_index=True)


def evidence_panel(name: str, role: str, screenshot: str, source: str, service_key: str) -> None:
    st.subheader(name)
    st.write(role)
    action = service_call_to_action(BACKEND_STATUS, SERVICE_REGISTRY[service_key])
    if action is not None:
        st.link_button(action[0], action[1], type="primary", width="stretch")
    st.image(str(SCREENSHOTS / screenshot), width="stretch")
    st.link_button(f"View {name} implementation", f"{REPOSITORY_URL}/blob/dev/{source}", width="stretch")


def pipeline_page() -> None:
    page_header(
        "Level 2 · Data platform",
        "Pipeline & storage",
        "Incremental ingestion, governed medallion layers, analytical processing and synchronization across Spark, dbt, PostgreSQL and Neo4j.",
        "Execution evidence",
    )
    backend_status_notice()
    st.markdown('<div class="flow"><strong>DATATOURISME</strong> → SHA-256 CDC → <strong>BRONZE</strong> → <strong>SILVER</strong> → SPARK / dbt / H3 / NEO4J</div>', unsafe_allow_html=True)
    st.subheader("Processing and analytics architecture")
    st.write("Spark and dbt branch from the trusted Silver layer, solve different transformation problems, and converge in the Gold decision layer.")
    with st.container(border=True):
        st.image(str(PROCESSING_ARCHITECTURE), width="stretch")
    left, right = st.columns(2)
    with left:
        evidence_panel("Airflow", "Runs the ordered Bronze → Silver → Spark → Gold → graph → dbt workflow with retries and task visibility.", "03-airflow-dag-grid.png", "airflow/dags/holiday_pipeline_dag.py", "airflow")
        evidence_panel("Spark", "Builds city-level analytical features from trusted Silver data and writes Parquet outputs.", "08-spark-master.png", "src/spark/city_feature_job.py", "spark")
    with right:
        evidence_panel("Postgres", "Stores raw JSONB, normalized relational tables, H3 clusters, and dbt marts.", "16-adminer-postgres-tables.png", "src/gold/postgres_warehouse.py", "adminer")
        st.subheader("dbt analytics layer")
        st.write("Defines staging models, city marts, category marts, schema tests, and source contracts.")
        st.code("dbt run --profiles-dir .\ndbt test --profiles-dir .", language="bash")
        st.link_button("View dbt models", f"{REPOSITORY_URL}/tree/dev/dbt/models", width="stretch")


def serving_page() -> None:
    page_header(
        "Level 1 · Product serving",
        "Serving, graph & events",
        "The request lifecycle from user intent to a multi-model itinerary response, graph enrichment and asynchronous product events.",
        "Execution evidence",
    )
    backend_status_notice()
    st.markdown('<div class="flow"><strong>STREAMLIT</strong> → FastAPI → POSTGRES + KMEANS + NEO4J → RESPONSE + KAFKA EVENTS</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        evidence_panel("FastAPI", "Validates contracts, retrieves Silver POIs, runs preference-aware KMeans grouping, and returns itinerary responses.", "02-fastapi-docs.png", "src/api/app.py", "fastapi")
        evidence_panel("Neo4j", "Traverses POI → City and POI → Category relationships to enrich stops with related-place recommendations.", "14-neo4j-browser.png", "src/gold/neo4j_graph_loader.py", "neo4j")
    with right:
        evidence_panel("Streamlit", "Collects preferences and presents itineraries, maps, weather, destinations, and place details.", "01-streamlit-dashboard.png", "src/api/dashboard.py", "streamlit")
        evidence_panel("Kafka", "Publishes weather snapshots and itinerary-generated events without blocking the user request.", "07-kafka-weather-messages.png", "src/streaming/kafka_events.py", "kafka")


def observability_page() -> None:
    page_header(
        "Level 3 · Platform operations",
        "Observability & product quality",
        "Operational telemetry, product-quality metrics, dashboards and alerts that answer both “is it healthy?” and “is it useful?”.",
        "Execution evidence",
    )
    backend_status_notice()
    st.markdown('<div class="flow"><strong>FASTAPI + PIPELINE METRICS</strong> → PROMETHEUS → GRAFANA → ALERTMANAGER</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        evidence_panel("Prometheus", "Scrapes request volume, latency, itinerary quality, weather suitability, route distance, and service health.", "12-prometheus-targets.png", "monitoring/prometheus/prometheus.yml", "prometheus")
    with right:
        evidence_panel("Grafana", "Combines operational and product KPIs into an engineer-facing platform dashboard.", "11-grafana-kpis.png", "monitoring/grafana/dashboards/holiday-platform.json", "grafana")
    st.subheader("Metrics that answer both ‘is it healthy?’ and ‘is it useful?’")
    metric_table = pd.DataFrame(
        [
            ("holiday_api_http_request_duration_seconds", "Operational", "API latency by endpoint"),
            ("holiday_itinerary_category_match_rate", "Product", "Preference alignment"),
            ("holiday_itinerary_avg_distance_km", "Product", "Route efficiency"),
            ("holiday_itinerary_weather_suitability_score", "Product", "Weather-aware suitability"),
        ],
        columns=["Metric", "Domain", "Decision supported"],
    )
    st.dataframe(metric_table, width="stretch", hide_index=True)
    st.link_button("View alert rules", f"{REPOSITORY_URL}/blob/dev/monitoring/prometheus/rules/holiday-alerts.yml")


def runbook_page() -> None:
    page_header(
        "Engineering runbook",
        "Run the complete platform",
        "A compact reproduction guide for reviewers who want to launch the full local data platform and inspect every service.",
        "Docker Compose",
    )
    backend_status_notice()
    st.code("docker compose up --build airflow-init\ndocker compose up --build -d", language="bash")
    st.subheader("Local service map")
    ports = pd.DataFrame(
        [
            ("Streamlit", "8501", "Product dashboard"), ("FastAPI", "8000/docs", "API contract"),
            ("Airflow", "8088", "DAG orchestration"), ("Kafka UI", "8090", "Topics and consumers"),
            ("Spark", "8080", "Cluster and jobs"), ("Grafana", "3000", "KPI dashboards"),
            ("Prometheus", "9090", "Metrics and targets"), ("Adminer", "5050", "Postgres inspection"),
        ],
        columns=["Service", "Local port", "Purpose"],
    )
    st.dataframe(ports, width="stretch", hide_index=True)
    st.link_button("Read the full repository guide", REPOSITORY_URL)


HOME_PAGE = st.Page(home_page, title="Project Home", icon="🏠", default=True)
APP_PAGE = st.Page(itinerary_page, title="Itinerary App", icon="🧭")
ARCHITECTURE_PAGE = st.Page(architecture_page, title="Architecture Details", icon="🧱")
PIPELINE_PAGE = st.Page(pipeline_page, title="Pipeline & Storage", icon="🔄")
SERVING_PAGE = st.Page(serving_page, title="Serving & Graph", icon="🔌")
OBSERVABILITY_PAGE = st.Page(observability_page, title="Observability", icon="📊")
RUNBOOK_PAGE = st.Page(runbook_page, title="Runbook", icon="📘")

st.sidebar.markdown(
    '<div class="sidebar-brand-card"><strong>Holiday Intelligence</strong><span>Data product control center</span></div>',
    unsafe_allow_html=True,
)

navigation = st.navigation(
    {
        "Start": [HOME_PAGE],
        "Explore": [APP_PAGE, ARCHITECTURE_PAGE, PIPELINE_PAGE, SERVING_PAGE, OBSERVABILITY_PAGE, RUNBOOK_PAGE],
    }
)
navigation.run()
