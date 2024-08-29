from typing import override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import Edge, Node


class RemoveToggledCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
    ):
        super().__init__(graph)

        self.nodes: dict[Node, any] = {}
        self.edges: dict[Edge, any] = {}

    def __remove_all(self):
        nodes = self.nodes.keys()
        self.graph.remove_nodes_from(nodes)

        edges = self.edges.keys()
        self.graph.remove_edges_from(edges)

    def __add_all(self):
        for node, data in self.nodes.items():
            self.graph.add_node(node, **data)

        for edge, data in self.edges.items():
            self.graph.add_edge(*edge, **data)

    def __find_all(self):
        # Find nodes that are set to be removed
        for node, data in self.graph.nodes(data=True):
            if "is_removed" in data and data["is_removed"]:
                self.nodes[node] = data

        # Find edges that are set to be removed
        for src, dst, key, data in self.graph.edges(keys=True, data=True):
            edge = (src, dst, key)

            if "is_removed" in data and data["is_removed"]:
                self.edges[edge] = data

    @override
    def execute(self):
        self.__find_all()
        self.__remove_all()

    @override
    def undo(self):
        self.__add_all()

    @override
    def redo(self):
        self.__remove_all()
