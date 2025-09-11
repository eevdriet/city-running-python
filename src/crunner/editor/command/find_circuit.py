from pathlib import Path
from typing import override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import contains_edge, find_node
from crunner.handler import Handler
from crunner.plotter import Plotter
from crunner.route import Postman


class FindCircuitCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph, path: Path, auto_circuit: bool = False):
        super().__init__(graph)

        self.path = path

        self.postman = Postman()
        self.plotter = Plotter()
        self.auto_circuit = auto_circuit
        self.circuit = []

    def toggled_removed(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        result = graph.copy()
        nodes = {}
        edges = {}

        # Find nodes that are set to be removed
        for node, data in result.nodes(data=True):
            if "is_removed" in data and data["is_removed"]:
                nodes[node] = data

        # Find edges that are set to be removed
        for src, dst, key, data in result.edges(keys=True, data=True):
            edge = (src, dst, key)

            if "is_removed" in data and data["is_removed"]:
                edges[edge] = data

        result.remove_nodes_from(nodes.keys())
        result.remove_edges_from(edges.keys())

        return result

    @override
    def execute(self):
        if self.auto_circuit:
            source = min(list(self.graph.nodes()))
        else:
            while True:
                # Ask for the source of the circuit
                source = input("Source of the circuit: ")
                if not source or not source.isdigit():
                    return

                # Find the circuit
                source = int(source)
                if self.graph.has_node(source):
                    break

                print(f"Node {source} is not in the graph, try again...")

        weights = {}

        if not self.auto_circuit:
            while True:
                try:
                    src, dst = map(int, input("Edge to add weight for: ").split("-"))
                    edge = tuple(sorted([src, dst]))
                    weight = int(input("Weight: "))
                    weights[edge] = weight
                except:
                    break

        print(f"Sourceee: {source}")
        graph = self.toggled_removed(self.graph)
        self.circuit, graph, self.stats = self.postman.rpp_undirected(
            graph, source, weights, self.auto_circuit
        )

        # Save the circuit
        self.plotter.plot_circuit(graph, self.circuit, self.path, self.stats)

    @override
    def undo(self):
        pass

    @override
    def redo(self):
        self.postman.rpp_undirected(self.graph, self.source)
