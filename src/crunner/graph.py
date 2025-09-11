from collections import deque
from enum import IntEnum
from itertools import pairwise
from typing import Optional

import networkx as nx
from geopy.distance import geodesic
from shapely import LineString

Coord = tuple[float, float]  # lat, lng
Node = int
Edge = tuple[Node, Node] | tuple[Node, Node, int]


def find_streets(graph: nx.MultiGraph) -> set[str]:
    streets = set()

    for _, _, data in graph.edges(data=True):
        if "name" not in data:
            continue

        street_names = data["name"]
        if isinstance(street_names, list):
            streets.update(street_names)
        else:
            streets.add(street_names)

    return streets


def find_odd_nodes(graph: nx.MultiGraph) -> list[Node]:
    return [node for node, degree in graph.degree if degree % 2 == 1]


def find_even_nodes(graph: nx.MultiGraph) -> list[Node]:
    return [node for node, degree in graph.degree if degree % 2 == 0]


def find_node_location(graph: nx.Graph, node_id: Node) -> Coord | tuple[None, None]:
    # Node doesn't exist
    if not graph.has_node(node_id):
        return None, None

    node = graph.nodes(data=True)[node_id]

    # Node data is incomplete
    if "x" not in node or "y" not in node:
        return None, None

    return node["y"], node["x"]


def find_center(graph: nx.Graph) -> Coord:
    lat = sum([node["y"] for _, node in graph.nodes(data=True)]) / len(graph.nodes())
    lng = sum([node["x"] for _, node in graph.nodes(data=True)]) / len(graph.nodes())

    return lat, lng


def find_edges(
    graph: nx.MultiGraph, src: int, dst: int, bi_directional: bool = True
) -> list[Edge]:
    normal = []

    if not graph.is_directed():
        return [(u, v, key) for u, v, key in graph.edges(src, dst, keys=True)]

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


def annotate_with_distances(graph: nx.MultiGraph) -> nx.MultiGraph:
    for src, dst, key, data in graph.edges(keys=True, data=True):
        # Already found distance, make sure it is numerical
        if False and "distance" in data:
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
    graph: nx.MultiDiGraph, src: int, dst: int, key: int = None
) -> list[Coord]:
    # For undirected edges
    is_reversed = False

    # Directed edge doesn't exist
    if not graph.has_edge(src, dst):
        is_reversed = True
        src, dst = dst, src

        if not graph.has_edge(src, dst):
            return []

    coords = []

    # Find coordinates from edge coordinates (for non-straight lines)
    if edge := graph.get_edge_data(src, dst, key):
        if 0 in edge:
            edge = edge[0]

        if "geometry" in edge and isinstance(edge["geometry"], LineString):
            xy_coords = list(edge["geometry"].coords)
            coords = [(y, x) for x, y in xy_coords]

    # Find coordinates directly from node end points (for straight lines)
    if not coords:
        coord_src = find_node_location(graph, src)
        coord_dst = find_node_location(graph, dst)

        if coord_src and coord_dst:
            coords = [coord_src, coord_dst]

    # Verify whether undirected edge needs to be reversed based on src, dst
    if not graph.is_directed():
        src_coord = find_node_location(graph, src)
        first_coord = coords[0]

        is_reversed = src_coord is not None and src_coord != first_coord

    if is_reversed:
        coords.reverse()

    return coords


def convert_to_simple_directed(graph: nx.MultiGraph) -> nx.Graph:
    result = graph.copy()

    # Keep track of a counter for the new nodes
    node = max(graph.nodes()) + 1

    for src, dst, key, data in graph.edges(keys=True, data=True):
        # Add the first edge normally
        # if not result.has_edge(src, dst):
        #     result.add_edge(src, dst, **data)
        #     continue
        if key == 0:
            continue

        print(f"Breaking up {src}, {dst} ({key})")
        result.remove_edge(src, dst, key)

        # Add a node at the mid point of the current multi edge
        y, x = find_edge_midpoint(graph, src, dst, key)
        result.add_node(node, **{"x": x, "y": y})

        # Split the straight line into two other straight lines
        if not ("geometry" in data and isinstance(data["geometry"], LineString)):
            result.add_edge(src, node, **data)
            result.add_edge(node, dst, **data)

        # Otherwise split the poly-line in two halfs
        else:
            first, second = split_linestring(data["geometry"])

            result.add_edge(src, node, **{**data, **{"geometry": first}})
            result.add_edge(node, dst, **{**data, **{"geometry": second}})

        node += 1

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


def normalize(G):
    G_normal = G.__class__()

    for u, v, data in G.edges(data=True):
        u_, v_ = sorted([u, v])

        if G.is_multigraph():
            for key in G[u][v]:
                G_normal.add_edge(u_, v_, key=key, **data)
        else:
            G_normal.add_edge(u_, v_, **data)

    for n, data in G.nodes(data=True):
        G_normal.add_node(n, **data)

    return G_normal


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
    graph: nx.MultiGraph, src: int, dst: int, key: Optional[int] = None
) -> Optional[Coord]:
    if edge := graph.get_edge_data(src, dst, key):
        edge = edge[0] if 0 in edge else edge

        if "geometry" in edge and isinstance(edge["geometry"], LineString):
            mid_point = edge["geometry"].interpolate(0.5, normalized=True)

            return mid_point.y, mid_point.x

    # Otherwise try to find mid point from node end points (for straight lines)
    y1, x1 = find_node_location(graph, src)
    y2, x2 = find_node_location(graph, dst)
    if not (y1 and x1 and y2 and x2):
        return None

    return (y1 + y2) / 2, (x1 + x2) / 2


def toggle_node_attr(graph: nx.MultiGraph, node: int, attr: str = "is_removed"):
    if not graph.has_node(node):
        print(f"WARNING: Node {node} doesn't exist, skipping...")
        return

    is_toggled = nx.get_node_attributes(graph, attr, default=False)
    attrs = {node: {attr: not is_toggled[node]}}

    nx.set_node_attributes(graph, attrs)


def toggle_edge_attr(
    graph: nx.MultiGraph,
    src: int,
    dst: int,
    key: int | None = None,
    attr: str = "is_removed",
):
    key = key if key is not None else 0
    id = (src, dst, key)

    # Edge doesn't exist: skip
    if not (graph.has_edge(src, dst) or graph.has_edge(dst, src)):
        print(f"WARNING: Edge {src} <-> {dst} doesn't exist, skipping...")
        return

    is_toggled = nx.get_edge_attributes(graph, attr, default=False)
    if id not in is_toggled:
        if graph.is_directed():
            print(f"Attribute '{attr}' not found for directed edge {id}")
            return

        id = (id[1], id[0], id[2])
        if id not in is_toggled:
            print(f"Attribute '{attr}' not found for undirected edge {id}")
            return

    attrs = {(src, dst, key): {attr: not is_toggled[id]}}
    nx.set_edge_attributes(graph, attrs)


class ToggleOption(IntEnum):
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
    graph: nx.MultiGraph, opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> list[set[Node]]:
    # If nodes cannot be toggled, find the components "the normal way"
    if opt == ToggleOption.NO_TOGGLE:
        return list(
            nx.weakly_connected_components(graph)
            if graph.is_directed()
            else nx.connected_components(graph)
        )

    # Determine how the graph is disconnected based on the `is_removed` node/edge property
    remove_graph = graph.copy()

    for node, data in graph.nodes(data=True):
        if data.get("is_removed", False) and remove_graph.has_node(node):
            remove_graph.remove_node(node)

    for src, dst, key, data in graph.edges(keys=True, data=True):
        if data.get("is_removed", False) and remove_graph.has_edge(src, dst, key):
            remove_graph.remove_edge(src, dst, key)

    return list(
        nx.weakly_connected_components(remove_graph)
        if remove_graph.is_directed()
        else nx.connected_components(remove_graph)
    )


def find_partitions_from_dist(
    graph: nx.MultiGraph, max_dist_m: float
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


def find_node(node_data: dict, search_graph: nx.MultiDiGraph):
    # Cannot make assumptions about nodes without geo location
    if "x" not in node_data or "y" not in node_data:
        return None

    x1, y1 = node_data["x"], node_data["y"]

    for node, other_data in search_graph.nodes(data=True):
        # Cannot compare nodes without geo location
        if "x" not in other_data or "y" not in other_data:
            continue

        # Nodes are the same when their position is equal
        x2, y2 = other_data["x"], other_data["y"]
        if x1 == x2 and y1 == y2:
            return node

    return None


def find_edge(
    src: int, dst: int, key: int, graph: nx.MultiDiGraph, search_graph: nx.MultiDiGraph
):
    edge = (src, dst, key)
    edge_data = graph.get_edge_data(*edge)

    # Compare lines
    if "geometry" in edge_data:
        line = edge_data["geometry"]

        for u, v, w, other_data in search_graph.edges(data=True, keys=True):
            other_edge = (u, v, w)

            # Edge is not defined from line
            if "geometry" not in other_data:
                continue

            # Verify whether lines are equal
            other_line = other_data["geometry"]

            if line == other_line or line.reverse() == other_line:
                return other_edge

    # Compare end points
    else:
        y1, x1 = find_node_location(graph, src)
        y2, x2 = find_node_location(graph, dst)

        # Cannot compare without end points
        if not (y1 and x1 and y2 and x2):
            return None

        for u, v, w, other_data in search_graph.edges(data=True, keys=True):
            other_edge = (u, v, w)

            # Edge is not defined from edge points
            if "geometry" in other_data:
                continue

            y3, x3 = find_node_location(search_graph, u)
            y4, x4 = find_node_location(search_graph, v)

            # Cannot compare without end points
            if not (y3 and x3 and y4 and x4):
                continue

            if (y1 == y3 and x1 == x3 and y2 == y4 and x2 == x4) or (
                y2 == y3 and x2 == x3 and y1 == y4 and x1 == x4
            ):
                return other_edge

    return None


def contains_node(node_data: dict, search_graph: nx.MultiDiGraph):
    return find_node(node_data, search_graph) is not None


def contains_edge(
    src: int, dst: int, key: int, graph: nx.MultiDiGraph, search_graph: nx.MultiDiGraph
):
    return find_edge(src, dst, key, graph, search_graph) is not None


def find_disconnected_elements(
    graph: nx.MultiDiGraph, opt: ToggleOption
) -> tuple[set[Node], set[Edge]]:
    no_disconnected_elems = set(), set()
    components = find_components(graph, opt)

    # Nothing disconnected for a single component
    if len(components) <= 1:
        return no_disconnected_elems

    # Keep the component that contains the given node
    main_component_idx = None

    match opt:
        case ToggleOption.KEEP_FROM_NODE:
            node_input = input("Enter node to keep component from: ")
            if not node_input:
                return no_disconnected_elems

            node = int(node_input)
            main_component_idx = next(
                (idx for idx, component in enumerate(components) if node in component),
                None,
            )
        case ToggleOption.KEEP_LARGEST:
            main_component_idx = max(
                range(len(components)), key=lambda idx: len(components[idx])
            )
        case ToggleOption.KEEP_ALL:
            return no_disconnected_elems

    if main_component_idx is None:
        return no_disconnected_elems

    # Remove main component and find all (disconnected) nodes and edges
    components.pop(main_component_idx)

    nodes = set()
    edges = set()

    for component in components:
        sub_graph = graph.subgraph(component)

        nodes.update(sub_graph.nodes)
        edges.update(sub_graph.edges)

    return nodes, edges


def make_edge(src: int, dst: int) -> tuple[int, int]:
    src, dst = sorted([src, dst])

    return src, dst
