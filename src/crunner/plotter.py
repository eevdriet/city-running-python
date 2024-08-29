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

from crunner.graph import *
from crunner.handler import Handler
from crunner.route import Postman

logger = setup_logger(__name__)

Circuit = list[tuple[int, int, any]]

# for idx, (coord, label) in enumerate(zip(coords, labels)):
#     # Add edges
#     folium.PolyLine(
#         [(y, x) for x, y in coord],
#         color="red",
#         weight=3,
#         opacity=0.8,
#         tooltip=label,
#     ).add_to(map)

# path = Path.cwd() / "data" / f"circuit.html"
# map.save(path)


class Plotter:
    def __get_node_positions(self, graph: nx.Graph) -> dict[int, tuple[int, int]]:
        return {node: (data["x"], data["y"]) for node, data in graph.nodes(data=True)}

    @classmethod
    def create_map(cls, graph: nx.Graph) -> folium.Map:
        center = find_center(graph)

        return folium.Map(center, zoom_start=16, max_zoom=25)

    @classmethod
    def create_line(
        cls, coords: list[Coord], color: str = "black", opacity: float = 1.0, **kwargs
    ) -> folium.PolyLine:
        return folium.PolyLine(locations=coords, color=color, opacity=opacity)

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
    def create_timed_lines2(
        cls, edges: list[list[Coord]]
    ) -> folium.plugins.TimestampedGeoJson:
        start = datetime(2024, 1, 1)
        end = start + timedelta(minutes=len(edges))

        # edge_data = [[(lon, lat) for lat, lon in edge] for edge in edges]
        edge_data = [
            (
                [(lon, lat) for lat, lon in edge],
                start + timedelta(minutes=itr),
            )
            for itr, edge in enumerate(edges)
        ]

        features = []
        for edge, timestamp in edge_data:
            # Add the currently walking feature
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

            # Add the already walked feature
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

        geojson_data = {"type": "FeatureCollection", "features": features}
        timeline = folium.plugins.Timeline(
            geojson_data,
            style=folium.utilities.JsCode(
                "function(data) { return data.properties.style; }"
            ),
        )

        timeline_slider = folium.plugins.TimelineSlider(
            auto_play=False,
            show_ticks=True,
            enable_keyboard_controls=True,
            playback_duration=300 * len(edges),
        )
        timeline_slider = timeline_slider.add_timelines(timeline)

        return timeline, timeline_slider

    def plot_odd_nodes(self, graph: nx.Graph):
        # Draw graph with all nodes
        fig, ax = ox.plot_graph(nx.MultiDiGraph(graph), show=False, close=False)
        node_pos = self.__get_node_positions(graph)

        nx.draw_networkx_nodes(
            graph,
            pos=node_pos,
            nodelist=[node for node, degree in graph.degree if degree % 2 == 1],
            node_size=20,
            node_color="red",
            # ax=ax,
        )
        nx.draw_networkx_labels(
            graph,
            pos=node_pos,
            labels={node: node for node in graph.nodes()},
            font_size=8,
            font_color="white",
            verticalalignment="top",
            # ax=ax,
        )

        plt.show()

    def plot_circuit(self, graph: nx.Graph, circuit: Circuit):
        if len(circuit) == 0:
            return

        logger.info("Plotting circuit...")
        source = circuit[0][0]

        # Setup map and nodes
        map = self.create_map(graph)

        # for node in graph.nodes():
        #     if (location := find_node_location(graph, node)) is not None:
        #         marker = self.create_marker(node, location)
        #         marker.add_to(map)

        if start_location := find_node_location(graph, source):
            start_marker = self.create_marker(
                source,
                start_location,
                color="white",
                background_color="red",
            )
            start_marker.add_to(map)

        edges = [find_edge_coords(graph, src, dst) for src, dst, _ in circuit]
        timeline, timeline_slider = self.create_timed_lines2(edges)
        timeline.add_to(map)
        timeline_slider.add_to(map)

        for itr, (src, dst, data) in enumerate(circuit, start=1):
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

            # if not "," in data["sequence"]:
            #     path = folium.plugins.AntPath(locations=coords, weight=10, delay=2000)
            #     path.add_to(map)

        path = Path.cwd() / "data" / f"out.html"
        map.save(path)
        logger.info("Graph explored!")


if __name__ == "__main__":
    from crunner.handler import Handler

    handler = Handler()
    path = Path("Rotterdam") / "Middelland-Zuid"
    graph = handler.load_from_file(path)

    SOURCE = 67
    circuit = Postman().rpp_undirected(graph, source=SOURCE)

    plotter = Plotter()
    plotter.plot_circuit(graph, circuit)
