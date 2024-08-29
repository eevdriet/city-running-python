from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import (
    Edge,
    Node,
    ToggleOption,
    find_disconnected_elements,
    toggle_edge_remove,
    toggle_node_remove,
)


class ToggleTypeCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph, typ: str, toggle_opt: ToggleOption):
        super().__init__(graph)
        self.typ = typ
        self.toggle_opt = toggle_opt

        self.nodes: set[Node] = set()
        self.nodes: set[Node] = set()

    def __toggle(self, nodes: set[Node], edges: set[Node]):
        for node in nodes:
            toggle_node_remove(self.graph, node)
        for edge in edges:
            toggle_edge_remove(self.graph, *edge)

    def __find_and_toggle(self):
        # Verify whether an edge of of a given type
        def is_type(highway: list[str] | str, typ: str):
            if isinstance(highway, list):
                return typ in highway
            if isinstance(highway, str):
                return highway == typ

            return False

        # Verify whether to toggle the type or everything else
        toggle_all = self.typ.startswith("-")
        self.typ = self.typ[1:] if toggle_all else self.typ

        # Find all edges with the given type
        self.edges = {
            (src, dst)
            for src, dst, data in self.graph.edges(data=True)
            if "highway" in data and (toggle_all != is_type(data["highway"], self.typ))
        }

        # Toggle all edges with typ
        self.__toggle(set(), self.edges)

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


def toggle_type_menu(
    graph: nx.MultiDiGraph, toggle_opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> Optional[ToggleTypeCommand]:
    output = input("Name type of edge to remove: ")
    if not output:
        return None

    return ToggleTypeCommand(graph, output, toggle_opt)
