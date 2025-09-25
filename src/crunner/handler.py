import copy
import json
import re
from ast import literal_eval
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import networkx as nx
import osmnx as ox
import polars as pl
import shapely
from veelog import setup_logger

from crunner.common import AREA_PATH, GRAPH_PATH, NON_RUNNABLE_ROADS, POLYGON_PATH
from crunner.graph import annotate_with_distances, find_edge_coords, toggle_edge_attr
from crunner.path import Paths

logger = setup_logger(__name__)


class Handler:
    """
    Loads graphs from OpenStreetMap using the OSMNX package
    Provides some default functionality for filtering non-runnable road types,
    as well as to filter unconnected components
    """

    DEFAULT_LOADING_ARGS = {
        "retain_all": True,
        "simplify": True,
    }
    CUSTOM_FILTERS = '["highway"]["area"!~"yes"]["highway"!~"abandoned|construction|no|planned|platform|proposed|raceway|razed|motorway|trunk"]["access"!~"private"]'

    # filters["all"] = (
    #     '["highway"]["area"!~"yes"]["highway"!~"abandoned|construction|no|planned|platform|'
    #     'proposed|raceway|razed"]'
    # )

    def __init__(self):
        self.__LOAD_FUNCS: list[tuple[str, str, Path, Callable]] = [
            (".graphml", "Graph", GRAPH_PATH, self.load_from_file),
            (".csv", "Polygon", POLYGON_PATH, self.load_from_polygon_file),
            (".json", "Area", AREA_PATH, self.load_from_area),
        ]
        self.__LOAD_MAP: dict[str, tuple[str, Path, Callable]] = {
            ext: args for ext, *args in self.__LOAD_FUNCS
        }

    def __create_graph_prompt(self, name: str):
        opts = "\n".join(
            (
                f"[{idx}] {label}"
                for idx, (label, _, _) in enumerate(self.__LOAD_MAP.values(), start=1)
            )
        )

        return f"""\
No extension given for "{name}", how would you like to load the graph?
--------------------------
--------------------------
{opts}
--------------------------
Enter here: """

    def __load_from_map(self, stem: str):
        prompt = self.__create_graph_prompt(stem)

        while True:
            output = input(prompt)
            if not output:
                break
            if not output.isdigit():
                continue

            idx = int(output) - 1
            if not (0 <= idx < len(self.__LOAD_MAP)):
                continue

            ext, _, base_path, load_func = self.__LOAD_FUNCS[idx]
            name = f"{stem}{ext}"

            for path in base_path.rglob("*"):
                if path.is_file() and path.name == name:
                    return load_func(path), path

            print(f"No path found for {stem}, try again...")

        return None, None

    def ask_for_graph2(
        self, suffix: str | None = None
    ) -> Optional[tuple[nx.MultiDiGraph, Path]]:
        try:
            name = Path(suffix if suffix else input("Give the name to the graph: "))
        except:
            return None

        path_types = {
            path: typ
            for path in Paths.find(name)
            if (typ := Paths.data_type(path)) in ["graph", "polygon", "area"]
        }

        path = None

        match len(path_types):
            case 0:
                print(f"No paths found for '{suffix}'")
            case 1:
                path = list(path_types.keys())[0]
            case _:
                if name.suffix == ".csv" and "graph" in path_types.values():
                    response = input(
                        "Are your sure you want to overwrite the existing graph? "
                    )
                    if response.lower().startswith("n"):
                        return None

                for _path, typ in path_types.items():
                    if _path.suffix == name.suffix:
                        path = _path
                        break
                else:
                    path = list(path_types.keys())[0]

        if path is None:
            return None

        _, _, load_func = self.__LOAD_MAP[path.suffix]
        return load_func(path), path

    def ask_for_graph(self) -> tuple[Optional[nx.MultiDiGraph], Optional[Path]]:
        name = input("Give the name to the graph: ")
        suffix_match = re.match(r"(.*)(\..*)", name)

        if not suffix_match:
            return self.__load_from_map(name)

        stem = suffix_match[1]
        suffix = suffix_match[2]
        _, base_path, load_func = self.__LOAD_MAP[suffix]

        if suffix == ".csv":
            for path in base_path.rglob("*.graphml"):
                if path.is_file() and path.stem == stem:
                    ans = input(
                        "Are you sure you want to override the existing graph with the CSV polygon? Y/N"
                    )
                    if ans.lower().strip() == "n":
                        return None, None

        path = base_path / name
        if path.exists():
            return load_func(path), path

        for subpath in base_path.rglob("*"):
            if subpath.is_file() and subpath.name == name:
                return load_func(subpath), subpath

        print(f"{path} does not exist, try without extension...")
        return self.__load_from_map(stem)

    @classmethod
    def __load(cls, load_func, load_with_args: bool = True, **kwargs):
        print("Loading graph...")

        # Load the graph
        args = {}
        if load_with_args:
            args = {**kwargs, **cls.DEFAULT_LOADING_ARGS}

        graph = load_func(**args)

        # Rename the nodes
        if max(graph.nodes()) > len(graph.nodes()) + 100:
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
        polygon: shapely.Polygon | shapely.MultiPolygon,
        **kwargs,
    ) -> nx.MultiDiGraph:
        load_func = partial(
            ox.graph_from_polygon,
            polygon=polygon,
            network_type="bike",
            # custom_filter=cls.CUSTOM_FILTERS,
            simplify=True,
        )

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
    def load_from_area(cls, path: Path) -> nx.Graph:
        with open(path, "r") as file:
            feature = json.load(file)
            coords = feature["geometry"]["coordinates"]
            polygon = shapely.MultiPolygon(coords)

        return cls.__load_from_polygon(polygon)

    @classmethod
    def load_from_file(cls, path: Path, **kwargs) -> nx.MultiDiGraph:
        print("Load from file", path)
        node_dtypes = {"lng": float, "lat": float}

        def load_graph(
            filepath: str | Path | None = None, *, graphml_str: str, node_dtypes
        ):
            graph = ox.load_graphml(
                filepath, graphml_str=graphml_str, node_dtypes=node_dtypes
            )

            for src, dst, key, data in graph.edges(data=True, keys=True):
                geometry = data.get("geometry")
                if geometry:
                    continue

                coords = data.get("coordinates")
                if not coords:
                    coords = find_edge_coords(graph, src, dst, key)
                    if not coords:
                        print(
                            f"No coordinates/geometry found for edge {src} -> {dst} ({key})"
                        )
                    else:
                        coords = [(x, y) for y, x in coords]
                        data["geometry"] = shapely.LineString(coords)
                    continue

                if isinstance(coords, shapely.LineString):
                    continue

                if isinstance(coords, list):
                    coords = shapely.LineString(coords)
                elif isinstance(coords, str):
                    # Literal (but string representation) of a line string
                    if re.match(r"LINESTRING\s*\((.*)\)", coords):
                        coords = shapely.from_wkt(coords)
                    else:
                        try:
                            # Coordinate list for the line string
                            coords = shapely.LineString(literal_eval(coords))
                        except:
                            continue
                else:
                    print(
                        f"Non-parsable coordinates found for edge {src} -> {dst} ({key}): {coords}"
                    )
                    continue

                data["geometry"] = coords
                del data["coordinates"]

            return graph

        with open(path, "r", encoding="utf-8") as file:
            graphml_str: str = file.read()
            graphml_str = re.sub(
                r'attr\.type="(.*)"', 'attr.type="string"', graphml_str
            )

            # Rename front
            graphml_str = graphml_str.replace('"lng"', '"x"').replace('"lat"', '"y"')
            graphml_str = graphml_str.replace("true", "True").replace("false", "False")
            # graphml_str = graphml_str.replace('"coordinates"', '"geometry"')

        load_func = partial(
            load_graph, graphml_str=graphml_str, node_dtypes=node_dtypes
        )

        return cls.__load(load_func, load_with_args=False)

    @classmethod
    def save(cls, G, path: Path):
        G_save = copy.deepcopy(G)
        graph_path = Paths.graph(path)

        renames = {"geometry": "coordinates", "x": "lng", "y": "lat"}

        # Rename back
        if G_save.is_multigraph():
            for u, v, key, data in G_save.edges(data=True, keys=True):
                for attr, new_attr in renames.items():
                    if attr in data:
                        data[new_attr] = data.pop(attr)

        ox.save_graphml(G_save, graph_path)

    @classmethod
    def __toggle_non_runnable_roads(
        cls, graph: nx.Graph, ask_for_removal: bool = False
    ):
        should_remove = True
        if ask_for_removal:
            remove_str = input("Remove non-runnable roads? ")
            should_remove = not remove_str or remove_str[0].lower() == "y"

        if should_remove:
            # Remove non-runnable roads
            edges_to_remove = [
                (src, dst, key)
                for src, dst, key, data in graph.edges(data=True, keys=True)
                if any(
                    road_type in data.get("highway", "")
                    for road_type in NON_RUNNABLE_ROADS
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
