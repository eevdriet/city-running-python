from functools import partial
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
from crunner.plotter2 import LeafletPlotter

logger = setup_logger(__name__)


class Explorer:
    """
    This class
    """

    def __init__(self):
        self.plotter = LeafletPlotter()

    @classmethod
    def explore_places(cls, parent_place: str):
        tags = {"place": True}
        df_geom = ox.features_from_place(parent_place, tags=tags)

        return list(sorted(df_geom["name"].dropna().unique()))

    def explore_roads(self, graph: nx.MultiDiGraph):
        logger.info("Exploring graph...")

        mapp = self.plotter.create_map(graph)

        def on_marker_clicked(marker, *args, **kwargs):
            icon = LeafletPlotter.create_icon(str(marker.node), background_color="red")
            print("Yeet")
            marker.icon = icon

            mapp.remove(marker)
            mapp.add(marker)

        # Add nodes to the map
        for node, data in graph.nodes(data=True):
            location = find_node_location(graph, node)

            is_removed = "is_removed" in data and data["is_removed"]
            kwargs = (
                {"color": "white", "background_color": "gray", "opacity": 0.5}
                if is_removed
                else {}
            )

            marker = self.plotter.create_marker(node, location, **kwargs)
            marker.on_click(partial(on_marker_clicked, marker))

            mapp.add(marker)

        # Add edges to map
        for *edge, data in graph.edges(data=True, keys=True):
            coords = find_edge_coords(graph, *edge)

            line = self.plotter.create_line(
                coords, color=ROAD_COLOR_MAP[data["highway"]], opacity=1, weight=3
            )
            line.edge = edge

            mapp.add(line)

        logger.info("Roads explored!")

        return mapp


if __name__ == "__main__":
    from crunner.handler import Handler

    path = Path("Rotterdam") / "Nieuwe Werk"
    graph = Handler.load_from_file(path)

    explorer = Explorer()
    explorer.explore_components(graph)
