from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import (
    Edge,
    Node,
    ToggleOption,
    find_disconnected_elements,
    find_edges,
    toggle_edge_remove,
    toggle_node_remove,
)


class ToggleElemCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        nodes: set[Node],
        edges: set[Edge],
        toggle_opt: ToggleOption,
    ):
        super().__init__(graph)

        self.nodes = nodes
        self.edges = edges
        self.toggle_opt = toggle_opt

    def __toggle(self, nodes: list[Node], edges: list[Edge]):
        for node in nodes:
            toggle_node_remove(self.graph, node)

        for src, dst, key in edges:
            if key is not None:
                toggle_edge_remove(self.graph, src, dst, key)
                continue

            for u, v, key in find_edges(self.graph, src, dst):
                toggle_edge_remove(self.graph, u, v, key)

    def __find_and_toggle(self):
        # Add edges that connect to the node to toggle
        for node in self.nodes:
            for edge in self.graph.in_edges(node, keys=True):
                self.edges.add(edge)
            for edge in self.graph.out_edges(node, keys=True):
                self.edges.add(edge)

        # Assign no key if none was given
        self.edges = {
            (src, dst, key[0] if len(tup) == 3 else None)
            for tup in self.edges
            for src, dst, *key in [tup]
        }

        self.__toggle(self.nodes, self.edges)

        # Also toggle all disconnected or reconnected parts
        if self.toggle_opt != ToggleOption.NO_TOGGLE:
            nodes, edges = find_disconnected_elements(self.graph, self.toggle_opt)
            self.__toggle(nodes, edges)

            self.nodes.update(nodes)
            self.edges.update(edges)

    @override
    def execute(self):
        self.__find_and_toggle()

    @override
    def undo(self):
        self.__toggle(self.nodes, self.edges)

    @override
    def redo(self):
        self.__toggle(self.nodes, self.edges)


def toggle_elem_menu(
    graph: nx.Graph, toggle_opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> Optional[ToggleElemCommand]:
    output = input(
        "List nodes/edges to remove (separate with , and separate nodes with -): "
    )
    if not output:
        return None

    nodes = {int(item) for item in output.split(",") if not "-" in item}
    edges = {
        tuple(map(int, item.split("-"))) for item in output.split(",") if "-" in item
    }

    return ToggleElemCommand(graph, nodes, edges, toggle_opt)
