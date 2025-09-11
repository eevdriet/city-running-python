from collections import Counter
from itertools import islice, pairwise
from typing import Optional

import networkx as nx
from veelog import setup_logger

from crunner.common import Circuit
from crunner.graph import *

logger = setup_logger(__name__)

NO_TURN_BACK_WEIGHT = 1000


class Postman:
    def __init__(self):
        self.graph_md: nx.MultiDiGraph | None = None
        self.graph_d: nx.DiGraph | None = None
        self.graph_u: nx.Graph | None = None

    def rpp_undirected(
        self,
        graph: nx.MultiDiGraph,
        source: Optional[int] = None,
        weights: dict[tuple[int, int], float] = {},
        use_largest_component: bool = False,
    ):
        # Verify the graph is connected to find circuit
        is_connected = (nx.is_directed(graph) and nx.is_weakly_connected(graph)) or (
            not nx.is_directed(graph) and nx.is_connected(graph)
        )
        if not is_connected:
            logger.info("Graph is not connected, pick component to work with")
            components = find_components(graph)
            components.sort(key=lambda c: len(c), reverse=True)

            if use_largest_component:
                idx = 0
            else:
                # List components (show 5 nodes or all if it has fewer)
                for n, component in enumerate(components, start=1):
                    n_nodes = len(component)
                    nodes = (
                        list(component) if n_nodes < 5 else list(islice(component, 5))
                    )
                    print(f"\tComponent {n} has {n_nodes} nodes: {nodes}")

                # Ask for component to keep
                output = input("Which component would you like to work with?: ")
                if not output or not output.isdigit():
                    return [], graph
                idx = int(output) - 1

            if not (0 <= idx < len(components)):
                return [], graph

            graph = nx.subgraph(graph, components[idx])

        # Change the graph into its undirected version
        self.graph_md = graph
        self.graph_d = convert_to_simple_directed(self.graph_md)

        self.graph_u = convert_to_simple_undirected(self.graph_d)
        self.graph_u = normalize(self.graph_u)

        # Find all pairs of odd nodes in the graph
        logger.info("Finding all odd nodes and their pairs...")
        odd_nodes = find_odd_nodes(self.graph_u)
        odd_graph = self.__create_complete_graph(odd_nodes)

        # Perform the minimum weight matching of all pairs of odd nodes
        logger.info("Finding minimum weight pairs of all odd notes...")
        min_matching = nx.algorithms.min_weight_matching(odd_graph, weight="distance")

        # Add minimum weight edges to original graph and find the circuit
        logger.info(
            "Add minimum weight edges to original graph and find the circuit..."
        )
        graph = self.__add_matching_to_graph(min_matching, self.graph_u)
        circuit = self.__find_euler_circuit(
            graph, self.graph_u, source=source, weights=weights
        )
        circuit, stats = self.collect_stats(circuit)

        self.__display_stats(stats)

        return circuit, graph, stats

    def __display_stats(self, stats: dict) -> None:
        dist = stats["total_distance_m"]
        dist_back = stats["total_distance_backtracked_m"]

        circuit = stats["circuit"]
        node_counts = Counter(node for edge in circuit for node in edge)
        n_multiple_node_visits = len(
            {node for node, count in node_counts.items() if count > 2}
        )

        print(
            f"""\
Circuit overview
--------------------------
Total distance (m): {round(dist / 1000, 3)}
    - New roads: {round((dist - dist_back) / 1000, 3)} ({round(100 * (dist - dist_back) / dist, 2)}%)
    - Backtracked: {round(dist_back / 1000, 3)} ({round(100 * (dist_back / dist), 2)}%)
Circuit | {circuit[0][0]} -> {circuit[0][1]} -> ... -> {circuit[-1][0]} -> {circuit[-1][1]}
    - Number of nodes: {stats['n_nodes']} ({n_multiple_node_visits} double visited)
    - Number of edges: {stats['n_edges']} ({stats['n_multiple_edge_visits']} double visited)
--------------------------
"""
        )

    def collect_stats(self, circuit: Circuit) -> dict:
        circuit_stats = {
            "source": circuit[0][0],
            "total_distance_m": 0.0,
            "total_distance_backtracked_m": 0.0,
            "percentage_backtracked": 0.0,
            "n_multiple_edge_visits": 0,
            "n_nodes": len({src for src, _, _ in circuit}),
            "n_edges": len(circuit),
            "circuit": [],
        }
        edge_stats = {}

        for idx, (src, dst, data) in enumerate(circuit):
            edge = tuple(sorted((src, dst)))

            circuit_stats["total_distance_m"] += data["distance"]
            circuit_stats["circuit"].append((src, dst))

            if edge in edge_stats:
                circuit_stats["total_distance_backtracked_m"] += data["distance"]
                circuit_stats["n_multiple_edge_visits"] += 1
                edge_stats[edge][2]["sequence"] += "," + str(idx)
                edge_stats[edge][2]["n_visits"] += 1
            else:
                edge_stats[edge] = (src, dst, data)
                edge_stats[edge][2]["sequence"] = str(idx)
                edge_stats[edge][2]["n_visits"] = 1

        circuit_stats["percentage_backtracked"] = (
            circuit_stats["total_distance_backtracked_m"]
            / circuit_stats["total_distance_m"]
        )

        new_circuit = []
        for src, dst, _ in circuit:
            edge = tuple(sorted((src, dst)))
            new_data = edge_stats[edge][2]

            new_circuit.append((src, dst, new_data))

        return new_circuit, circuit_stats

    def __find_weight(self, u: int, v: int, data: dict) -> float:
        # Weight is distance if the edge is traversable normally
        dist = data["distance"]
        if self.graph_d.has_edge(u, v):
            return dist

        # For one-way cycle lanes, double the weight
        road_type = data.get("highway", "unclassified")
        if road_type.startswith("cycle"):
            return 2 * dist

        return dist

    def __find_shortest_dist_weight(self, src: int, dst: int) -> float:
        shortest_path = self.__find_shortest_path(src, dst)
        dist, weight = 0, 0

        for curr, nxt in pairwise(shortest_path):
            edge_data = self.graph_u.get_edge_data(curr, nxt)
            dist += edge_data["distance"]
            weight += self.__find_weight(curr, nxt, edge_data)

        return dist, weight

    def __find_shortest_path(self, src: int, dst: int) -> float:
        # return nx.shortest_path(self.graph_u, src, dst, weight=self.__find_weight)
        return nx.shortest_path(self.graph_u, src, dst, weight="distance")

    def __find_naieve_euler_circuit(
        self,
        graph: nx.Graph,
        source: Optional[int] = None,
        edge_weights: dict[tuple[int, int], float] = {},
    ) -> list[tuple[int, int]]:
        if len(graph.nodes) == 0:
            return []

        G = graph.copy()

        source = source if source else 0
        circuit = []

        def choose_next_vertex(
            curr_vertex: int, last_vertex: Optional[int] = None
        ) -> Optional[int]:
            best_vertex = None
            best_weight = float("inf")
            edges = G.edges(curr_vertex)

            for _, next_vertex in edges:
                edge: tuple[int, int] = make_edge(curr_vertex, next_vertex)

                if next_vertex == last_vertex and edge not in edge_weights:
                    edge_weights[edge] = NO_TURN_BACK_WEIGHT

                weight = edge_weights.get(edge, 0)

                if weight < best_weight:
                    best_vertex = next_vertex
                    best_weight = weight

            return best_vertex

        vertex_stack = [source]
        last_vertex = None
        while vertex_stack:
            current_vertex = vertex_stack[-1]

            if G.degree(current_vertex) == 0:
                if last_vertex is not None:
                    edge = (last_vertex, current_vertex)
                    circuit.append(edge)

                vertex_stack.pop()
            else:
                next_vertex = choose_next_vertex(current_vertex, last_vertex)
                if next_vertex is None:
                    break

                vertex_stack.append(next_vertex)
                G.remove_edge(current_vertex, next_vertex)

            last_vertex = current_vertex

        circuit = [edge[::-1] for edge in circuit][::-1]
        print(f"Circuit: {circuit}")
        return circuit

    def __find_euler_circuit(
        self,
        graph_aug: nx.Graph,
        graph_orig: nx.Graph,
        source: Optional[int] = None,
        weights: dict[tuple[int, int], float] = {},
    ) -> Circuit:
        # Define the resulting circuit and the naive circuit that it builds from
        circuit = []
        naive_circuit = self.__find_naieve_euler_circuit(graph_aug, source, weights)

        for src, dst in naive_circuit:
            data = graph_aug.get_edge_data(src, dst)[0]

            # Edge was not augmented: take over from naive circuit
            if "augmented" not in data:
                circuit.append((src, dst, data))
                continue

            # Edge was augmented: reconstruct
            min_path = nx.shortest_path(graph_orig, src, dst, weight="distance")
            min_pairs = list(zip(min_path[:-1], min_path[1:]))

            for frm, to in min_pairs:
                data = graph_orig[frm][to]
                circuit.append((frm, to, data))

        return circuit

    def __add_matching_to_graph(
        self, matching: set[tuple[int, int]], graph: nx.Graph
    ) -> nx.Graph:
        graph_result = nx.MultiGraph(graph.copy())
        matching = {tuple(sorted(item)) for item in matching}

        for src, dst in matching:
            dist, weight = self.__find_shortest_dist_weight(src, dst)
            attrs = {
                "distance": dist,
                "weight": weight,
                "augmented": True,
            }
            graph_result.add_edge(src, dst, **attrs)

        return graph_result

    def __create_complete_graph(self, nodes: list[Node]) -> nx.Graph:
        logger.info("Creating complete graph of odd nodes...")
        graph: nx.Graph = nx.complete_graph(nodes)

        for src, dst in graph.edges:
            dist, weight = self.__find_shortest_dist_weight(src, dst)
            attrs = {"distance": dist, "weight": weight}

            graph[src][dst].update(attrs)

        return graph
