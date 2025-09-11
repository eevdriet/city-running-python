from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import Edge, Node, ToggleOption, find_disconnected_elements


class ToggleRemovedCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        nodes: set[Node],
        edges: set[Edge],
        toggle_opt: ToggleOption,
    ):
        super().__init__(graph)

        self.nodes = {node for node in nodes if self.graph.has_node(node)}
        self.edges = {edge for edge in edges if self.graph.has_edge(*edge)}
        self.toggle_opt = toggle_opt

    def __find_and_toggle(self):
        # Add edges that connect to the node to toggle
        for node in self.nodes:
            for edge in self.graph.edges(node, keys=True):
                self.edges.add(edge)
            # for edge in self.graph.in_edges(node, keys=True):
            #     self.edges.add(edge)
            # for edge in self.graph.out_edges(node, keys=True):
            #     self.edges.add(edge)

        # Assign no key if none was given
        self.edges = {
            (src, dst, key[0] if len(tup) == 3 else None)
            for tup in self.edges
            for src, dst, *key in [tup]
        }

        print(self.edges)
        self._toggle(self.nodes, self.edges)

        # Also toggle all disconnected or reconnected parts
        if self.toggle_opt != ToggleOption.NO_TOGGLE:
            nodes, edges = find_disconnected_elements(self.graph, self.toggle_opt)
            self._toggle(nodes, edges)

            self.nodes.update(nodes)
            self.edges.update(edges)

    @override
    def execute(self):
        self.__find_and_toggle()

    @override
    def undo(self):
        self._toggle(self.nodes, self.edges)

    @override
    def redo(self):
        self._toggle(self.nodes, self.edges)


def toggle_menu(
    graph: nx.Graph, toggle_opt: ToggleOption = ToggleOption.NO_TOGGLE
) -> Optional[ToggleRemovedCommand]:
    #     108-109,6
    # 4-106,314-23
    output = input(
        "List nodes/edges to toggle (separate with , and separate nodes with -): "
    )
    if not output:
        return None

    if output == "all":
        nodes = {
            node
            for node, data in graph.nodes(data=True)
            if "is_removed" in data and data["is_removed"]
        }
        edges = {
            (src, dst, key)
            for src, dst, key, data in graph.edges(data=True, keys=True)
            if "is_removed" in data and data["is_removed"]
        }
    else:
        output = output.replace(" ", "")
        nodes = {int(item) for item in output.split(",") if not "-" in item}
        edges = {
            tuple(map(int, item.split("-")))
            for item in output.split(",")
            if "-" in item
        }

    return ToggleRemovedCommand(graph, nodes, edges, toggle_opt)
