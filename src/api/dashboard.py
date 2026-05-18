"""Streamlit dashboard for the Holiday Itinerary FastAPI service."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(
    page_title="Holiday Itinerary Dashboard",
    layout="wide",
)


st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d8dee9;
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }
        .place-panel {
            border: 1px solid #d8dee9;
            border-radius: 8px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.75rem;
            background: #ffffff;
        }
        .muted { color: #667085; font-size: 0.9rem; }
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


@st.cache_data(ttl=60)
def load_summary():
    return api_get("/summary")


@st.cache_data(ttl=60)
def load_cities():
    return api_get("/cities", limit=100)


@st.cache_data(ttl=300)
def load_categories():
    return api_get("/categories", limit=300)


st.title("Holiday Itinerary Dashboard")
st.caption(f"Connected to `{API_BASE_URL}`")

try:
    health = api_get("/health")
except requests.RequestException as exc:
    st.error(
        f"FastAPI is not reachable at {API_BASE_URL}. Start the API service first."
    )
    st.exception(exc)
    st.stop()

if not health.get("database_ready"):
    st.warning(
        "The API is running, but `silver_places` is not loaded yet. Run the ETL pipeline first."
    )
    st.stop()

try:
    summary = load_summary()
    cities = load_cities()
    categories = load_categories()
except requests.RequestException as exc:
    st.error("The API responded, but the dashboard could not load project data.")
    st.exception(exc)
    st.stop()

metric_cols = st.columns(4)
metric_cols[0].metric("Places", f"{summary['places']:,}")
metric_cols[1].metric("Cities", f"{summary['cities']:,}")
metric_cols[2].metric("Categories", f"{summary['categories']:,}")
metric_cols[3].metric("Gold clusters", f"{summary['clusters']:,}")

st.divider()

left, right = st.columns([0.32, 0.68], gap="large")

with left:
    st.subheader("Plan")
    city_options = [item["city"] for item in cities]
    if not city_options:
        st.warning("No city data is available yet.")
        st.stop()
    city = st.selectbox("City", options=city_options, index=0)
    days = st.slider("Days", min_value=1, max_value=7, value=3)
    max_places = st.slider("Places per day", min_value=1, max_value=8, value=5)
    generate = st.button("Generate itinerary", type="primary", width="stretch")

    st.subheader("Explore")
    selected_categories = st.multiselect(
        "Interests",
        options=categories,
        placeholder="All categories",
    )
    place_limit = st.slider(
        "Places to show", min_value=10, max_value=200, value=50, step=10
    )

with right:
    view = st.segmented_control(
        "View",
        options=["Itinerary", "Places", "Cities"],
        default="Itinerary",
        label_visibility="collapsed",
    )

    if view == "Itinerary":
        if not city:
            st.info("No city data is available yet.")
        elif generate:
            with st.spinner(
                "Building itinerary from silver POIs and graph recommendations..."
            ):
                try:
                    itinerary = api_post(
                        "/generate-itinerary",
                        {
                            "city": city,
                            "days": days,
                            "max_places_per_day": max_places,
                            "categories": selected_categories,
                        },
                    )
                except requests.HTTPError as exc:
                    detail = exc.response.json().get("detail", str(exc))
                    st.error(detail)
                    itinerary = []

            for day in itinerary:
                st.markdown(f"### Day {day['day']}")
                for place in day["places"]:
                    categories_text = (
                        ", ".join(place["categories"][:3]) or place["category"]
                    )
                    recommendations = (
                        ", ".join(place["recommendations"]) or "No graph match yet"
                    )
                    st.markdown(
                        f"""
                        <div class="place-panel">
                            <strong>{place['start_time']} - {place['end_time']} | {place['name']}</strong>
                            <div class="muted">{categories_text}</div>
                            <div>{place.get('address') or ''}</div>
                            <div class="muted">Related: {recommendations}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                day_df = pd.DataFrame(day["places"])
                if not day_df.empty:
                    st.map(
                        day_df.rename(columns={"lat": "latitude", "lon": "longitude"})
                    )
        else:
            st.info("Choose a city and generate an itinerary.")

    if view == "Places":
        params = {"city": city, "limit": place_limit}
        if selected_categories:
            params["categories"] = selected_categories
        try:
            places = api_get("/places", **params)
        except requests.RequestException as exc:
            st.error("Could not load places.")
            st.exception(exc)
            places = []

        places_df = pd.DataFrame(places)
        if places_df.empty:
            st.info("No places match the selected filters.")
        else:
            map_df = places_df.rename(columns={"lat": "latitude", "lon": "longitude"})
            st.map(map_df[["latitude", "longitude"]])
            table_df = places_df[
                ["name", "city", "address", "categories", "website"]
            ].copy()
            table_df["categories"] = table_df["categories"].apply(
                lambda value: ", ".join(value or [])
            )
            st.dataframe(table_df, width="stretch", hide_index=True)

    if view == "Cities":
        cities_df = pd.DataFrame(cities)
        st.bar_chart(cities_df.set_index("city")["poi_count"].head(25))
        st.dataframe(cities_df, width="stretch", hide_index=True)
