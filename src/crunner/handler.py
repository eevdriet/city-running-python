from functools import partial
from pathlib import Path
from typing import Optional

import networkx as nx
import osmnx as ox
import polars as pl
import shapely
from veelog import setup_logger

from crunner.common import GRAPH_PATH, NON_RUNNABLE_ROADS, POLYGON_PATH
from crunner.graph import annotate_with_distances, toggle_edge_attr, toggle_node_attr

logger = setup_logger(__name__)


class Handler:
    """
    Loads graphs from OpenStreetMap using the OSMNX package
    Provides some default functionality for filtering non-runnable road types,
    as well as to filter unconnected components
    """

    DEFAULT_LOADING_ARGS = {
        "network_type": "all",
        "retain_all": True,
        "simplify": True,
    }

    @classmethod
    def __load(cls, load_func, load_with_args: bool = True, **kwargs):
        # Load the graph
        args = {}
        if load_with_args:
            args = {**kwargs, **cls.DEFAULT_LOADING_ARGS}

        graph = load_func(**args)

        # Convert to simple
        # graph = nx.Graph(graph)

        # Rename the nodes
        node_ids = {node: id for id, node in enumerate(graph.nodes())}
        graph = nx.relabel_nodes(graph, node_ids)

        # Edit the graph
        graph = cls.__remove_multiple_road_types(graph)
        graph = cls.__toggle_non_runnable_roads(graph)
        graph = annotate_with_distances(graph)

        return graph

    @classmethod
    def load_from_place(cls, place: str, **kwargs) -> nx.MultiDiGraph:
        load_func = partial(ox.graph_from_place, query=place)

        return cls.__load(load_func, **kwargs)

    @classmethod
    def __load_from_polygon(
        cls,
        polygon: shapely.Polygon,
        **kwargs,
    ) -> nx.MultiDiGraph:
        load_func = partial(ox.graph_from_polygon, polygon=polygon)

        return cls.__load(load_func, **kwargs)

    @classmethod
    def __load_polygon(cls, path: Path) -> shapely.Polygon:
        df = pl.read_csv(path, has_header=True)
        coords = list(df.iter_rows())

        return shapely.Polygon(coords)

    @classmethod
    def load_from_polygon_file(cls, path: Path) -> nx.Graph:
        path = POLYGON_PATH / path.with_suffix("").with_suffix(".csv")
        polygon = cls.__load_polygon(path)

        return cls.__load_from_polygon(polygon)

    @classmethod
    def load_from_file(cls, path: Path, **kwargs) -> nx.MultiDiGraph:
        path = GRAPH_PATH / path.with_suffix("").with_suffix(".graphml")
        load_func = partial(ox.load_graphml, filepath=path)

        return cls.__load(load_func, load_with_args=False)

    @classmethod
    def save(cls, graph: nx.Graph, path: Path):
        path = GRAPH_PATH / path.with_suffix("").with_suffix(".graphml")
        ox.save_graphml(graph, path)

    @classmethod
    def __toggle_non_runnable_roads(cls, graph: nx.Graph):
        # Remove non-runnable roads
        edges_to_remove = [
            (src, dst, key)
            for src, dst, key, data in graph.edges(data=True, keys=True)
            if any(
                road_type in data.get("highway", "") for road_type in NON_RUNNABLE_ROADS
            )
        ]

        for src, dst, key in edges_to_remove:
            toggle_edge_attr(graph, src, dst, key, "is_removed")

        # Remove orphaned nodes only connecting to those roads
        # nodes_to_remove = [node for node, degree in graph.degree if degree == 0]
        # graph.remove_nodes_from(nodes_to_remove)

        return graph

    @classmethod
    def __remove_multiple_road_types(cls, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        def normalize(roads):
            return roads[0] if isinstance(roads, list) else roads

        for _, _, edge in graph.edges(data=True):
            if "highway" in edge:
                edge["highway"] = normalize(edge["highway"])

        return graph
