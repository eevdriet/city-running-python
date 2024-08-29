from itertools import combinations
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from veelog import setup_logger

from crunner.graph import *
from crunner.handler import Handler

logger = setup_logger(__name__)


class Postman:
    def rpp_undirected(self, graph: nx.MultiDiGraph, source: Optional[int] = None):
        # Change the graph into its undirected version
        self.graph = nx.Graph(graph)

        if not nx.is_connected(self.graph):
            logger.info("Graph is not connected, exiting...")
            return []

        # Find all pairs of odd nodes in the graph
        logger.info("Finding all odd nodes and their pairs...")
        odd_nodes = find_odd_nodes(self.graph)
        odd_graph = self.__create_complete_graph(odd_nodes)

        # Perform the minimum weight matching of all pairs of odd nodes
        logger.info("Finding minimum weight pairs of all odd notes...")
        min_matching = nx.algorithms.min_weight_matching(odd_graph, weight="distance")

        # Add minimum weight edges to original graph and find the circuit
        logger.info(
            "Add minimum weight edges to original graph and find the circuit..."
        )
        graph = self.__add_matching_to_graph(min_matching, self.graph)

        return self.__find_euler_circuit(graph, self.graph, source=source)

    def __collect_stats(self, circuit):
        circuit_stats = {
            "total_distance_m": 0.0,
            "total_distance_backtracked_m": 0.0,
            "percentage_backtracked": 0.0,
            "n_multiple_edge_visits": 0,
            "n_nodes": len({src for src, _, _ in circuit}),
            "n_edges": len(circuit),
        }
        edge_stats = {}

        for idx, (src, dst, data) in enumerate(circuit):
            edge = tuple(sorted((src, dst)))

            circuit_stats["total_distance_m"] += data["distance"]

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

        print(circuit_stats)

        new_circuit = []
        for src, dst, _ in circuit:
            edge = tuple(sorted((src, dst)))
            new_data = edge_stats[edge][2]

            new_circuit.append((src, dst, new_data))

        return new_circuit

    def __find_euler_circuit(
        self, graph_aug: nx.Graph, graph_orig: nx.Graph, source: Optional[int] = None
    ):
        # Define the resulting circuit and the naive circuit that it builds from
        circuit = []
        naive_circuit = list(nx.eulerian_circuit(graph_aug, source=source))

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

        return self.__collect_stats(circuit)

    def __add_matching_to_graph(
        self, matching: set[tuple[int, int]], graph: nx.Graph
    ) -> nx.Graph:
        graph_result = nx.MultiGraph(graph.copy())
        matching = {tuple(sorted(item)) for item in matching}

        for src, dst in matching:
            attrs = {
                "distance": nx.shortest_path_length(graph, src, dst, weight="distance"),
                "augmented": True,
            }
            graph_result.add_edge(src, dst, **attrs)

        return graph_result

    def __find_shortest_distances(
        self, pairs: list[tuple[int, int]]
    ) -> dict[tuple[int, int], float]:
        logger.info("Find shortest distances between all given pairs...")
        distances = {}

        for src, dst in pairs:
            distance = nx.shortest_path_length(self.graph, src, dst, weight="distance")
            distances[(src, dst)] = distance

        return distances

    def __create_complete_graph(self, nodes: list[Node]):
        logger.info("Creating complete graph of odd nodes...")
        graph = nx.Graph()

        pairs = combinations(nodes, r=2)
        for src, dst in pairs:
            distance = nx.shortest_path_length(self.graph, src, dst, weight="distance")
            attrs = {"distance": distance}

            graph.add_edge(src, dst, **attrs)

        return graph


if __name__ == "__main__":
    graph = Handler.load_from_place("Landzicht, Rotterdam, Netherlands")
    postman = Postman()
    circuit = postman.rpp_undirected(graph)

    print("Done")
