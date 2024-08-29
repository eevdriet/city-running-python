from itertools import pairwise
from typing import Optional

import networkx as nx
from geopy.distance import geodesic
from shapely import LineString

Coord = tuple[float, float]  # lat, lng
Node = int
Edge = tuple[Node, Node] | tuple[Node, Node, int]


def find_odd_nodes(graph: nx.Graph) -> list[Node]:
    return [node for node, degree in graph.degree if degree % 2 == 1]


def find_even_nodes(graph: nx.Graph) -> list[Node]:
    return [node for node, degree in graph.degree if degree % 2 == 0]


def find_node_location(graph: nx.Graph, node_id: Node) -> Optional[Coord]:
    # Node doesn't exist
    if not graph.has_node(node_id):
        return None

    node = graph.nodes(data=True)[node_id]

    # Node data is incomplete
    if "x" not in node or "y" not in node:
        return None

    return node["y"], node["x"]


def find_center(graph: nx.Graph) -> Coord:
    lat = sum([node["y"] for _, node in graph.nodes(data=True)]) / len(graph.nodes())
    lng = sum([node["x"] for _, node in graph.nodes(data=True)]) / len(graph.nodes())

    return lat, lng


def find_edges(graph: nx.MultiDiGraph, src: int, dst: int, bi_directional: bool = True):
    normal = [(u, v, key) for u, v, key in graph.out_edges(src, keys=True) if v == dst]

    if not bi_directional:
        return normal

    reverse = [(u, v, key) for u, v, key in graph.out_edges(dst, keys=True) if v == src]
    return normal + reverse


def annotate_with_distances(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    for src, dst, key, data in graph.edges(keys=True, data=True):
        # Already found distance, make sure it is numerical
        if "distance" in data:
            data["distance"] = float(data["distance"])
            continue

        # Find the distance from the coordinates of the edge
        coords = find_edge_coords(graph, src, dst)
        distance = sum(geodesic(curr, nxt).meters for curr, nxt in pairwise(coords))

        # Save it to the resulting graph
        attrs = {(src, dst, key): {"distance": distance}}
        nx.set_edge_attributes(graph, attrs)

    return graph


def find_edge_coords(graph: nx.Graph, src: int, dst: int) -> list[Coord]:
    is_reversed = False

    # Edge doesn't exist
    if not graph.has_edge(src, dst):
        is_reversed = True
        src, dst = dst, src

        if not graph.has_edge(src, dst):
            return []

    result = []

    # Find coordinates from edge geometry (for non-straight lines)
    if edge := graph.get_edge_data(src, dst):
        edge = edge[0]

        if "geometry" in edge and isinstance(edge["geometry"], LineString):
            xy_coords = list(edge["geometry"].coords)
            result = [(y, x) for x, y in xy_coords]

    # Find coordinates directly from node end points (for straight lines)
    if not result:
        coord_src = find_node_location(graph, src)
        coord_dst = find_node_location(graph, dst)

        if coord_src and coord_dst:
            result = [coord_src, coord_dst]

    if is_reversed:
        result.reverse()

    return result


def find_edge_midpoint(graph: nx.Graph, src: int, dst: int) -> Optional[Coord]:
    if edge := graph.get_edge_data(src, dst):
        edge = edge[0]

        if "geometry" in edge and isinstance(edge["geometry"], LineString):
            mid_point = edge["geometry"].interpolate(0.5, normalized=True)

            return mid_point.y, mid_point.x

    # Otherwise try to find mid point from node end points (for straight lines)
    y1, x1 = find_node_location(graph, src)
    y2, x2 = find_node_location(graph, dst)

    return (y1 + y2) / 2, (x1 + x2) / 2


def convert_to_undirected(graph: nx.MultiDiGraph) -> nx.Graph:
    result = nx.Graph()


def toggle_node_remove(graph: nx.MultiDiGraph, node: int):
    if not graph.has_node(node):
        print(f"WARNING: Node {node} doesn't exist, skipping...")
        return

    is_removed = nx.get_node_attributes(graph, "is_removed", default=False)
    attrs = {node: {"is_removed": not is_removed[node]}}
    nx.set_node_attributes(graph, attrs)


def toggle_edge_remove(graph: nx.MultiDiGraph, src: int, dst: int, key: int = None):
    key = key if key is not None else 0

    # Edge doesn't exist: skip
    if not (graph.has_edge(src, dst) or graph.has_edge(dst, src)):
        print(f"WARNING: Edge {src} <-> {dst} doesn't exist, skipping...")
        return

    is_removed = nx.get_edge_attributes(graph, "is_removed", default=False)

    attrs = {(src, dst, key): {"is_removed": not is_removed[(src, dst, key)]}}
    nx.set_edge_attributes(graph, attrs)


class ToggleOption:
    NO_TOGGLE = 0
    KEEP_LARGEST = 1
    KEEP_FROM_NODE = 2


def find_disconnected_elements(
    graph: nx.MultiDiGraph, opt: ToggleOption
) -> tuple[set[Node], set[Edge]]:
    if opt == ToggleOption.NO_TOGGLE:
        return set(), set()

    # Determine how the graph is disconnected based on the `is_removed` node/edge property
    remove_graph = graph.copy()

    for node, data in graph.nodes(data=True):
        if data.get("is_removed", False) and remove_graph.has_node(node):
            remove_graph.remove_node(node)

    for src, dst, key, data in graph.edges(keys=True, data=True):
        if data.get("is_removed", False) and remove_graph.has_edge(src, dst, key):
            remove_graph.remove_edge(src, dst, key)

    # Keep the component that contains the given node
    components = list(nx.weakly_connected_components(remove_graph))
    main_component_idx = None

    if opt == ToggleOption.KEEP_FROM_NODE is not None:
        node = int(input("Enter node to keep component from: "))
        main_component_idx = next(
            (idx for idx, component in enumerate(components) if node in component)
        )

    # If no node given or not found in any component, keep the largest component
    if main_component_idx is None:
        main_component_idx = max(
            range(len(components)), key=lambda idx: len(components[idx])
        )

    # Remove main component and find all (disconnected) nodes and edges
    components.pop(main_component_idx)
    nodes = set()
    edges = set()

    for component in components:
        sub_graph = graph.subgraph(component)

        nodes.update(sub_graph.nodes)
        edges.update(sub_graph.edges)

    return nodes, edges
