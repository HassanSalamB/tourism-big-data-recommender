"""Browser-compatible Leaflet maps for itinerary places."""

from __future__ import annotations

from html import escape
from typing import Any, Iterable

import folium
import streamlit as st
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

OPENSTREETMAP_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OPENSTREETMAP_ATTRIBUTION = "&copy; OpenStreetMap contributors"


def build_leaflet_map(places: Iterable[dict[str, Any]]) -> folium.Map | None:
    """Build an OpenStreetMap-backed route map without requiring WebGL."""
    valid_places = [place for place in places if place.get("lat") is not None and place.get("lon") is not None]
    if not valid_places:
        return None

    coordinates = [(float(place["lat"]), float(place["lon"])) for place in valid_places]
    center = [
        sum(latitude for latitude, _ in coordinates) / len(coordinates),
        sum(longitude for _, longitude in coordinates) / len(coordinates),
    ]
    route_map = folium.Map(
        location=center,
        tiles=OPENSTREETMAP_TILES,
        attr=OPENSTREETMAP_ATTRIBUTION,
        zoom_start=13,
        control_scale=True,
        zoom_control=True,
    )
    route_map.get_root().header.add_child(
        folium.Element(
            """
            <style>
              .leaflet-tile-pane {
                filter: grayscale(0.45) saturate(0.75) brightness(1.08);
              }
            </style>
            """
        )
    )
    Fullscreen(position="topright", title="Open fullscreen", title_cancel="Exit fullscreen").add_to(route_map)

    if len(coordinates) > 1:
        route_map.fit_bounds(coordinates, padding=(28, 28))

    for position, (place, coordinate) in enumerate(zip(valid_places, coordinates), start=1):
        name = escape(str(place.get("name", "Place")))
        address = escape(str(place.get("address", "")))
        categories = escape(", ".join(str(category) for category in place.get("categories", [])[:3]))
        popup = folium.Popup(
            f"<strong>{position}. {name}</strong><br>{categories}<br>{address}",
            max_width=280,
        )
        folium.CircleMarker(
            location=coordinate,
            radius=9,
            color="#075e54",
            weight=2,
            fill=True,
            fill_color="#24b995",
            fill_opacity=0.9,
            tooltip=f"{position}. {name}",
            popup=popup,
        ).add_to(route_map)

    return route_map


def render_leaflet_map(places: Iterable[dict[str, Any]], *, key: str, height: int = 500) -> None:
    """Render a responsive Leaflet map or a useful empty-state message."""
    route_map = build_leaflet_map(places)
    if route_map is None:
        st.info("Map coordinates are unavailable for these places.")
        return

    st_folium(
        route_map,
        key=key,
        height=height,
        use_container_width=True,
        returned_objects=[],
    )
