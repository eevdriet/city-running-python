from pathlib import Path

import folium
import geopandas as gpd
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely import Polygon
from veelog import setup_logger

from crunner.common import HTML_PATH, ROAD_COLOR_MAP
from crunner.graph import *
from crunner.plotter import Plotter

logger = setup_logger(__name__)


class Explorer:
    """
    This class
    """

    def __init__(self):
        self.plotter = Plotter()

    @classmethod
    def explore_places(cls, parent_place: str):
        tags = {"place": True}
        df_geom = ox.features_from_place(parent_place, tags=tags)

        return list(sorted(df_geom["name"].dropna().unique()))

    def explore_components(self, graph: nx.MultiDiGraph):
        nodes, edges = find_disconnected_elements(graph, ToggleOption.KEEP_LARGEST)
        print("Disconnected")
        print(f"\tNodes: {nodes}")
        print(f"\tEdges: {edges}")

        map = self.plotter.create_map(graph)

        for node in nodes:
            location = find_node_location(graph, node)

            marker = self.plotter.create_marker(node, location)
            marker.add_to(map)

        for edge in edges:
            coords = find_edge_coords(graph, *edge)

            line = self.plotter.create_line(
                coords,
            )
            line.add_to(map)

        path = HTML_PATH / f"map.html"
        map.save(path)
        logger.info("Components explored!")

    def explore_roads(self, graph: nx.MultiDiGraph):
        logger.info("Exploring graph...")

        # Add a new column to df with the color based on the highway type
        df_edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)
        if df_edges.crs != "EPSG:4326":
            df_edges = df_edges.to_crs(epsg=4326)

        # Normalize the highway type (only have the first)
        def normalize(roads):
            if isinstance(roads, list):  # If highway is a list, take the first one
                return roads[0]

            return roads

        df_edges["highway"] = df_edges["highway"].apply(normalize)
        df_edges["color"] = df_edges["highway"].apply(
            lambda val: ROAD_COLOR_MAP.get(val, "#000000")
        )

        # Determine whether an edge is a bridge
        bridges = set(nx.bridges(nx.MultiGraph(graph)))

        def is_bridge(row):
            src, dst, *_ = tuple(map(int, row.name))

            return (src, dst) in bridges or (dst, src) in bridges

        df_edges["is_bridge"] = df_edges.apply(is_bridge, axis=1)

        # Filter edges on whether removed or not
        if "is_removed" not in df_edges.columns:
            df_edges["is_removed"] = False
        if "is_highlighted" not in df_edges.columns:
            df_edges["is_highlighted"] = False

        mask = (df_edges["is_removed"] == False) | (df_edges["is_removed"].isnull())
        mask2 = (df_edges["is_highlighted"] == False) | (
            df_edges["is_highlighted"].isnull()
        )
        df_edges_normal = df_edges[mask]
        df_edges_remove = df_edges[~mask]
        df_edges_bridge = df_edges_normal[df_edges_normal["is_bridge"]]
        df_edges_highlight = df_edges_normal[~mask2]

        df = pd.DataFrame(df_edges)

        # Create road map
        mapp = df_edges_normal.explore(
            column="highway",  # The column to visualize
            legend=True,
            color=df_edges_normal["color"],
            style_kwds={"weight": 5},
            zoom_start=16,
            max_zoom=25,
        )

        # Add bridges to the map
        for (src, dst, _), data in df_edges_bridge.iterrows():
            coords = find_edge_coords(graph, src, dst)
            line = Plotter.create_line(
                coords,
                color="red",
                weight=8,
                opacity=1.0,
            )
            line.add_to(mapp)

        # Add highlights to map
        for (src, dst, _), data in df_edges_highlight.iterrows():
            coords = find_edge_coords(graph, src, dst)
            line = Plotter.create_line(
                coords,
                color="blue",
                weight=10,
                opacity=1.0,
            )
            line.add_to(mapp)

        # Add nodes to the map
        for node, data in graph.nodes(data=True):
            if (location := find_node_location(graph, node)) is not None:
                is_removed = "is_removed" in data and data["is_removed"]
                kwargs = (
                    {"color": "white", "background_color": "gray", "opacity": 0.5}
                    if is_removed
                    else {}
                )

                line = Plotter.create_marker(node, location, **kwargs)
                line.add_to(mapp)

        # Add edges to map
        for (src, dst, _), data in df_edges_remove.iterrows():
            coords = find_edge_coords(graph, src, dst)

            if (location := find_edge_midpoint(graph, src, dst)) is not None:
                line = Plotter.create_line(
                    coords,
                    color="gray",
                    opacity=0.3,
                )
                line.add_to(mapp)

        path = HTML_PATH / f"map.html"
        mapp.save(path)
        logger.info("Roads explored!")


if __name__ == "__main__":
    from crunner.handler import Handler

    path = Path("Rotterdam") / "Nieuwe Werk"
    graph = Handler.load_from_file(path)

    explorer = Explorer()
    explorer.explore_components(graph)
