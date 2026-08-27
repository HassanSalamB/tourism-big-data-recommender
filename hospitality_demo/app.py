"""Reviewer-facing Streamlit app for the accommodation intelligence demo."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hospitality_demo.pipeline import run_demo_pipeline


st.set_page_config(
    page_title="Accommodation Intelligence Lab",
    page_icon="🏨",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 1220px; padding-top: 1.5rem;}
      [data-testid="stMetric"] {border: 1px solid #dce4e8; border-radius: 12px; padding: 12px 16px;}
      .notice {padding: 12px 16px; border-radius: 10px; background: #eef7f4; border: 1px solid #b9ddd2;}
      .action {padding: 14px 16px; margin: 8px 0; border-left: 4px solid #13795b; background: #f7faf9;}
      .muted {color: #5b6870; font-size: 0.92rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_demo():
    return run_demo_pipeline()


demo = load_demo()
quality = demo["quality_summary"]

st.title("Accommodation Intelligence Lab")
st.caption("From fragmented accommodation observations to trusted properties and explainable commercial actions")
st.markdown(
    """
    <div class="notice">
      <strong>Independent portfolio prototype.</strong> This demo uses synthetic data and public hospitality concepts.
      It is not affiliated with Lighthouse and contains no Lighthouse source code, data, or confidential information.
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(5)
metric_columns[0].metric("Source rows", quality["source_rows"])
metric_columns[1].metric("Canonical properties", quality["canonical_properties"])
metric_columns[2].metric("Duplicates merged", quality["duplicate_rows_merged"])
metric_columns[3].metric("Quality pass rate", f"{quality['quality_pass_rate']:.1f}%")
metric_columns[4].metric("Checks executed", quality["checks_run"])

market_tab, matching_tab, quality_tab, architecture_tab = st.tabs(
    ["Market pulse", "Property resolution", "Data quality", "Engineering notes"]
)

with market_tab:
    st.subheader("Explainable decision support")
    st.write(
        "Recommendations are generated only after source records are resolved into canonical properties. "
        "Every action exposes its evidence instead of presenting an unexplained AI answer."
    )

    properties_by_id = {
        item["canonical_id"]: item for item in demo["canonical_properties"]
    }
    for action in demo["recommendations"]:
        icon = {"high": "🔴", "medium": "🟠", "low": "🟢"}[action["priority"]]
        st.markdown(
            f"""
            <div class="action">
              <strong>{icon} {action['property']}: {action['action']}</strong><br>
              {action['reason']}<br>
              <span class="muted">Evidence combined from {action['evidence_sources']} source(s).</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    selected_name = st.selectbox(
        "Inspect source rates",
        options=[item["name"] for item in demo["canonical_properties"]],
    )
    selected = next(item for item in demo["canonical_properties"] if item["name"] == selected_name)
    rate_frame = pd.DataFrame(selected["records"])[
        ["source", "room_rate", "available_rooms", "demand_index", "observed_at"]
    ]
    st.bar_chart(rate_frame.set_index("source")["room_rate"], color="#13795b")
    st.dataframe(rate_frame, width="stretch", hide_index=True)

with matching_tab:
    st.subheader("Cross-source entity resolution")
    st.write(
        "Candidate pairs combine normalized name similarity, address similarity, and geographic distance. "
        "High-confidence pairs are merged automatically; uncertain pairs would be routed to review."
    )
    pair_frame = pd.DataFrame(demo["candidate_pairs"])
    st.dataframe(
        pair_frame[
            [
                "left_name",
                "right_name",
                "name_similarity",
                "address_similarity",
                "distance_km",
                "match_score",
                "decision",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    canonical_rows = []
    for item in demo["canonical_properties"]:
        canonical_rows.append(
            {
                "canonical_id": item["canonical_id"],
                "name": item["name"],
                "city": item["city"],
                "sources": ", ".join(item["sources"]),
                "source_records": ", ".join(item["source_records"]),
                "rate_spread_pct": item["rate_spread_pct"],
                "latest_observation": item["latest_observation"],
            }
        )
    st.subheader("Canonical accommodation facts")
    st.dataframe(pd.DataFrame(canonical_rows), width="stretch", hide_index=True)

with quality_tab:
    st.subheader("Quality and freshness controls")
    check_columns = st.columns(3)
    check_columns[0].metric("Passed", quality["checks_passed"])
    check_columns[1].metric("Failed / warned", quality["checks_run"] - quality["checks_passed"])
    check_columns[2].metric("Pass rate", f"{quality['quality_pass_rate']:.1f}%")

    issues = pd.DataFrame(demo["quality_issues"])
    if issues.empty:
        st.success("No data quality issues detected.")
    else:
        st.dataframe(issues, width="stretch", hide_index=True)

    st.markdown(
        """
        Current controls include required-field validation, coordinate availability, rate availability,
        observation freshness, duplicate detection, and traceability from canonical properties back to source IDs.
        In production, the same outputs would feed data contracts, freshness SLOs, alerts, and catalog lineage.
        """
    )

with architecture_tab:
    st.subheader("Architecture and design decisions")
    st.code(
        """Source feeds / APIs
        |
        v
Raw immutable observations + source lineage
        |
        v
Normalization -> quality checks -> candidate generation
        |
        v
Explainable entity resolution -> canonical accommodation facts
        |
        +--> rate, demand, availability features
        |
        v
Commercial decision rules / ML features -> APIs, analytics, AI products""",
        language="text",
    )

    st.markdown(
        """
        **Why this small demo exists**

        The main repository contains the production-style Airflow, Spark, Kafka, dbt, Postgres, Neo4j,
        Prometheus, and Grafana platform. This application is deliberately lightweight so a reviewer can
        understand the data-product thinking in a few minutes without provisioning the complete stack.

        **What I would add at scale**

        - BigQuery-partitioned accommodation facts and observation history
        - Pub/Sub or Kafka inputs for rate and availability changes
        - dbt contracts and freshness tests
        - Precision/recall measurement plus a human-review queue for uncertain matches
        - Catalog ownership, lineage, quality SLOs, and cost observability
        - Learned ranking or recommendation models trained only after the facts layer is trustworthy
        """
    )
