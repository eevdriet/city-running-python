import json
from datetime import datetime, timedelta
from pathlib import Path

import folium
import folium.plugins
import folium.utilities
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from veelog import setup_logger

from crunner.common import HTML_PATH
from crunner.graph import *
from crunner.handler import Handler
from crunner.route import Postman

logger = setup_logger(__name__)

Circuit = list[tuple[int, int, any]]


class Plotter:
    @classmethod
    def create_map(cls, graph: nx.Graph) -> folium.Map:
        center = find_center(graph)

        return folium.Map(center, zoom_start=16, max_zoom=25)

    @classmethod
    def create_line(
        cls,
        coords: list[Coord],
        color: str = "black",
        opacity: float = 1.0,
        weight: float = 2.0,
        **kwargs,
    ) -> folium.PolyLine:
        return folium.PolyLine(
            locations=coords, color=color, opacity=opacity, weight=weight
        )

    @classmethod
    def create_marker(cls, text: str, location: Coord, **kwargs) -> folium.Marker:
        return folium.Marker(
            radius=kwargs.get("radius", 2),
            color="black",
            icon=folium.DivIcon(
                html=f"""<div style="
                        background-color: {kwargs.get("background_color", "yellow")};
                        border: 2px solid black;
                        border-radius: 2px;
                        padding: 0px 5px;
                        text-align: start;
                        font-size: 10px;
                        font-weight: bold;
                        opacity: {kwargs.get("opacity", 1.0)};
                        position: absolute;
                        left: 50%;
                        transform: translateX(-50%);
                        color: {kwargs.get("color", "black")};">{text}</div>"""
            ),
            fill_opacity=0.1,
            location=location,
        )

    @classmethod
    def create_timeline(
        cls, edges: list[list[Coord]]
    ) -> folium.plugins.TimestampedGeoJson:
        # Determine start and end "date" of the edges to display
        start = datetime(2024, 1, 1)
        end = start + timedelta(minutes=len(edges))

        # Display each edge for one segment
        edge_data = [
            (
                [(lon, lat) for lat, lon in edge],
                start + timedelta(minutes=itr),
            )
            for itr, edge in enumerate(edges)
        ]

        # Create features from all edges
        features = []
        for edge, timestamp in edge_data:
            # Add the currently walking edge
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": edge,
                    },
                    "properties": {
                        "start": timestamp.isoformat(),
                        "end": (timestamp + timedelta(minutes=1)).isoformat(),
                        "style": {"color": "red", "weight": 5},
                    },
                }
            )

            # Add the already walked edges
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": edge,
                    },
                    "properties": {
                        "start": (timestamp + timedelta(minutes=1)).isoformat(),
                        "end": end.isoformat(),
                        "style": {"color": "grey", "weight": 5},
                    },
                }
            )

        # Transform the features into JSON data and create time line
        geojson_data = {"type": "FeatureCollection", "features": features}
        timeline = folium.plugins.Timeline(
            geojson_data,
            style=folium.utilities.JsCode(
                "function(data) { return data.properties.style; }"
            ),
        )

        # Create slider for the timeline
        timeline_slider = folium.plugins.TimelineSlider(
            auto_play=False,
            show_ticks=True,
            enable_keyboard_controls=True,
            playback_duration=600 * len(edges),
        )
        timeline_slider = timeline_slider.add_timelines(timeline)

        return timeline, timeline_slider

    def plot_circuit(self, graph: nx.Graph, circuit: Circuit):
        if len(circuit) == 0:
            return

        logger.info("Plotting circuit...")
        source = circuit[0][0]

        # Setup map and nodes
        map = self.create_map(graph)

        # Add the start location
        if start_location := find_node_location(graph, source):
            start_marker = self.create_marker(
                source,
                start_location,
                color="white",
                background_color="red",
            )
            start_marker.add_to(map)

        # Add a timeline of all traversed edges in the circuit
        edges = [find_edge_coords(graph, src, dst) for src, dst, _ in circuit]
        timeline, timeline_slider = self.create_timeline(edges)
        timeline.add_to(map)
        timeline_slider.add_to(map)

        # Label edges that are traversed more than once
        for src, dst, data in circuit:
            n_visits = data["n_visits"]
            if n_visits > 1:
                mid_point = find_edge_midpoint(graph, src, dst)
                seq_marker = self.create_marker(
                    n_visits,
                    location=mid_point,
                    color="white",
                    background_color="green",
                )
                seq_marker.add_to(map)

        # Save the circuit map
        path = HTML_PATH / f"circuit.html"
        map.save(path)
        logger.info("Circuit explored!")


if __name__ == "__main__":
    from crunner.handler import Handler

    handler = Handler()
    path = Path("Rotterdam") / "Middelland-Zuid"
    graph = handler.load_from_file(path)

    SOURCE = 67
    circuit = Postman().rpp_undirected(graph, source=SOURCE)

    plotter = Plotter()
    plotter.plot_circuit(graph, circuit)
