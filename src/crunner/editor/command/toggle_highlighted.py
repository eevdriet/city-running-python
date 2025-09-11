from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import (
    Edge,
    Node,
    ToggleOption,
    find_disconnected_elements,
    find_edges,
    toggle_edge_attr,
    toggle_node_attr,
)


class TogglePropertyCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        nodes: set[Node],
        edges: set[Edge],
        prop: str = "is_highlighted",
    ):
        super().__init__(graph)

        self.nodes = nodes
        self.edges = edges
        self.prop = prop

    @override
    def execute(self):
        self._toggle(self.nodes, self.edges, self.prop)

    @override
    def undo(self):
        self._toggle(self.nodes, self.edges, self.prop)

    @override
    def redo(self):
        self._toggle(self.nodes, self.edges, self.prop)


def toggle_highlighted_menu(
    graph: nx.Graph, toggle_opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> Optional[TogglePropertyCommand]:
    #     108-109,6
    # 4-106,314-23
    output = input(
        "List nodes/edges to toggle (separate with , and separate nodes with -): "
    )
    if not output:
        return None

    output = output.replace(" ", "")
    nodes = {int(item) for item in output.split(",") if not "-" in item}
    edges = {
        tuple(map(int, item.split("-"))) for item in output.split(",") if "-" in item
    }

    return TogglePropertyCommand(graph, nodes, edges)
