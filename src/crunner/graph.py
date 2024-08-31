from collections import deque
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


def find_edges(
    graph: nx.MultiDiGraph, src: int, dst: int, bi_directional: bool = True
) -> list[Edge]:
    normal = []

    if src in graph:
        normal = [
            (u, v, key) for u, v, key in graph.out_edges(src, keys=True) if v == dst
        ]

        if not bi_directional:
            return normal

    if dst in graph:
        reverse = [
            (u, v, key) for u, v, key in graph.out_edges(dst, keys=True) if v == src
        ]

        return normal + reverse

    return []


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


def find_edge_coords(
    graph: nx.Graph, src: int, dst: int, key: int = None
) -> list[Coord]:
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


def convert_to_simple_undirected(graph: nx.MultiDiGraph) -> nx.Graph:
    # Keep track of a counter for the new nodes
    result = nx.Graph()
    node_id = max(graph.nodes()) + 1

    for node, data in graph.nodes(data=True):
        result.add_node(node, **data)

    for src, dst, key, data in graph.edges(keys=True, data=True):
        # Add the first edge normally
        if not result.has_edge(src, dst):
            result.add_edge(src, dst, **data)
            continue

        if key == 0:
            continue

        # Split the edge for multiple edges between the same nodes
        node = node_id
        node_id += 1

        y, x = find_edge_midpoint(graph, src, dst, key)
        result.add_node(node, **{"x": x, "y": y})

        if not ("geometry" in data and isinstance(data["geometry"], LineString)):
            result.add_edge(src, node, **data)
            result.add_edge(node, dst, **data)
        else:
            first, second = split_linestring(data["geometry"])
            result.add_edge(src, node, **{**data, **{"geometry": first}})
            result.add_edge(node, dst, **{**data, **{"geometry": second}})

    return result


def split_linestring(line: LineString) -> tuple[LineString, LineString]:
    # Find the length and middle of the line
    total_len = line.length
    mid_point = line.interpolate(total_len / 2).coords[0]

    # Split the line such that each half has the same length
    coords = list(line.coords)
    split_idx = next(
        idx
        for idx in range(1, len(coords))
        if LineString(coords[: idx + 1]).length >= total_len / 2
    )

    # Create both halves from the coordinates before/after the split
    first = LineString(coords[: split_idx + 1] + [mid_point])
    second = LineString([mid_point] + coords[split_idx:])

    return first, second


def find_edge_midpoint(
    graph: nx.MultiDiGraph, src: int, dst: int, key: Optional[int] = None
) -> Optional[Coord]:
    if edge := graph.get_edge_data(src, dst):
        edge = edge[0]

        if "geometry" in edge and isinstance(edge["geometry"], LineString):
            mid_point = edge["geometry"].interpolate(0.5, normalized=True)

            return mid_point.y, mid_point.x

    # Otherwise try to find mid point from node end points (for straight lines)
    y1, x1 = find_node_location(graph, src)
    y2, x2 = find_node_location(graph, dst)

    return (y1 + y2) / 2, (x1 + x2) / 2


def toggle_node_attr(graph: nx.MultiDiGraph, node: int, attr: str = "is_removed"):
    if not graph.has_node(node):
        print(f"WARNING: Node {node} doesn't exist, skipping...")
        return

    is_toggled = nx.get_node_attributes(graph, attr, default=False)
    attrs = {node: {attr: not is_toggled[node]}}

    nx.set_node_attributes(graph, attrs)


def toggle_edge_attr(
    graph: nx.MultiDiGraph,
    src: int,
    dst: int,
    key: int = None,
    attr: str = "is_removed",
):
    key = key if key is not None else 0

    # Edge doesn't exist: skip
    if not (graph.has_edge(src, dst) or graph.has_edge(dst, src)):
        print(f"WARNING: Edge {src} <-> {dst} doesn't exist, skipping...")
        return

    is_toggled = nx.get_edge_attributes(graph, attr, default=False)
    attrs = {(src, dst, key): {attr: not is_toggled[(src, dst, key)]}}

    nx.set_edge_attributes(graph, attrs)


class ToggleOption:
    NO_TOGGLE = 0
    KEEP_LARGEST = 1
    KEEP_FROM_NODE = 2
    KEEP_ALL = 3


def total_length(graph: nx.MultiDiGraph, count_removed: bool = False):
    graph_u = convert_to_simple_undirected(graph)
    result = 0

    for src, dst, data in graph_u.edges(data=True):
        if not "distance" in data:
            print(f"WARNING: Edge {(src, dst)} has no distance")
            continue

        if "is_removed" in data and data["is_removed"] and count_removed:
            continue

        result += data["distance"]

    return result


def find_components(
    graph: nx.MultiDiGraph, opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> list[set[Node]]:
    # If nodes cannot be toggled, find the components "the normal way"
    if opt == ToggleOption.NO_TOGGLE:
        return list(nx.weakly_connected_components(graph))

    # Determine how the graph is disconnected based on the `is_removed` node/edge property
    remove_graph = graph.copy()

    for node, data in graph.nodes(data=True):
        if data.get("is_removed", False) and remove_graph.has_node(node):
            remove_graph.remove_node(node)

    for src, dst, key, data in graph.edges(keys=True, data=True):
        if data.get("is_removed", False) and remove_graph.has_edge(src, dst, key):
            remove_graph.remove_edge(src, dst, key)

    return list(nx.weakly_connected_components(remove_graph))


def find_partitions_from_dist(
    graph: nx.MultiDiGraph, max_dist_m: float
) -> list[set[Edge]]:
    graph_u = convert_to_simple_undirected(graph)

    partitions = []
    visited: set[Edge] = set()

    def bfs(start_node: Node):
        to_explore = deque([start_node])
        partition = set()
        curr_dist = 0

        while to_explore:
            node = to_explore.popleft()

            if node in visited:
                continue

            visited.add(node)

            for neighbor in graph_u.neighbors(node):
                edge = (node, neighbor)
                data = graph_u.get_edge_data(*edge)
                dist = data["distance"]

                if curr_dist + dist <= max_dist_m:
                    partition.add(edge)
                    to_explore.append(neighbor)
                    curr_dist += dist

        return partition, curr_dist

    n = 1
    for node in graph_u.nodes:
        if not node in visited:
            partition, dist = bfs(node)
            partitions.append(partition)

            print(f"Partition {n} has distance of {dist}m")
            n += 1

    return partitions


def find_disconnected_elements(
    graph: nx.MultiDiGraph, opt: ToggleOption
) -> tuple[set[Node], set[Edge]]:
    components = find_components(graph, opt)

    # Nothing disconnected for a single component
    if len(components) <= 1:
        return set(), set()

    # Keep the component that contains the given node
    main_component_idx = None
    if opt == ToggleOption.KEEP_FROM_NODE is not None:
        node = int(input("Enter node to keep component from: "))
        main_component_idx = next(
            (idx for idx, component in enumerate(components) if node in component), None
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
