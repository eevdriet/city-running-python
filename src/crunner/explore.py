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

from crunner.color import ROAD_COLOR_MAP
from crunner.graph import *
from crunner.plotter import Plotter

logger = setup_logger(__name__)


class Explorer:
    """
    This class
    """

    @classmethod
    def explore_places(cls, parent_place: str):
        tags = {"place": True}
        df_geom = ox.features_from_place(parent_place, tags=tags)

        return list(sorted(df_geom["name"].dropna().unique()))

    def explore_components(self, graph: nx.MultiDiGraph):
        components = list(nx.weakly_connected_components(graph))

        color_map = matplotlib.colormaps.get_cmap("tab10")
        colors = [mcolors.to_hex(color_map(idx)) for idx in range(len(components))]

        # Create road map
        map = folium.Map(location=find_center(graph), zoom_start=13)

        for idx, (color, component) in enumerate(zip(colors, components)):
            sub_graph = nx.MultiDiGraph(graph.subgraph(component))
            nodes = list(sub_graph.nodes())
            edges = list(sub_graph.edges())

            print(f"Component {idx + 1} has {len(nodes)} node and {len(edges)} edges")
            df_nodes = (
                ox.graph_to_gdfs(sub_graph, nodes=True, edges=False)
                if len(nodes) > 0
                else gpd.GeoDataFrame()
            )
            df_edges = (
                ox.graph_to_gdfs(sub_graph, nodes=False, edges=True)
                if len(edges) > 0
                else gpd.GeoDataFrame()
            )

            # Add nodes to the map
            for idx, node in df_nodes.iterrows():
                folium.CircleMarker(
                    radius=2 if len(edges) > 0 else 10,
                    color="black",
                    tooltip=node.name,
                    popup=f"Node ID: {idx}",
                    fill_opacity=0.9,
                    location=[node["y"], node["x"]],
                ).add_to(map)

                folium.map.Marker(
                    [node["y"] + 0.5, node["x"]],
                    icon=folium.DivIcon(
                        icon_size=(50, 18),
                        icon_anchor=(0, 0),
                        html=f'<div style="font-size: 24pt">{node.name}</div>',
                    ),
                ).add_to(map)

            # Add edges to the map
            for idx, edge in df_edges.iterrows():
                geometry = edge["geometry"]
                if not geometry:
                    continue

                folium.PolyLine(
                    locations=[(lat, lng) for lng, lat in list(geometry.coords)],
                    color=color,
                    weight=2,
                    opacity=0.9,
                ).add_to(map)

        path = Path.cwd() / "data" / f"out.html"
        map.save(path)
        logger.info("Graph explored!")

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

        # Filter edges on whether removed or not
        if "is_removed" not in df_edges.columns:
            df_edges["is_removed"] = False

        mask = (df_edges["is_removed"] == False) | (df_edges["is_removed"].isnull())
        df_edges_normal = df_edges[mask]
        df_edges_remove = df_edges[~mask]

        # Create road map
        map = df_edges_normal.explore(
            column="highway",  # The column to visualize
            color=df_edges["color"],
            zoom_start=16,
            max_zoom=25,
        )

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
                line.add_to(map)

        # Add edges to map
        for (src, dst, _), data in df_edges_remove.iterrows():
            coords = find_edge_coords(graph, src, dst)

            if (location := find_edge_midpoint(graph, src, dst)) is not None:
                line = Plotter.create_line(
                    coords,
                    color="gray",
                    opacity=0.3,
                )
                line.add_to(map)

        path = Path.cwd() / "data" / f"out.html"
        map.save(path)
        logger.info("Graph explored!")


if __name__ == "__main__":
    from crunner.handler import Handler

    # graph = Handler.load_from_file("Katendrecht")
    graph = Handler.load_from_place("Landzicht, Rotterdam, Netherlands")
    explorer = Explorer()
    explorer.explore_components(graph)
