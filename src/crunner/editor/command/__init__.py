from abc import ABC, abstractmethod
from typing import Callable, Optional

import networkx as nx

from crunner.graph import Edge, Node, find_edges, toggle_edge_attr, toggle_node_attr


def input_nodes_edges(command_str: str = "") -> tuple[set[Node], set[Edge]]:
    output = input(
        f"List nodes/edges {command_str} (separate with , and separate edge nodes with -): "
    )
    if not output:
        return set(), set()

    nodes = {int(item) for item in output.split(",") if not "-" in item}
    edges = {
        tuple(map(int, item.split("-"))) for item in output.split(",") if "-" in item
    }

    return nodes, edges


class Command(ABC):
    def __init__(self, graph: nx.MultiGraph):
        self.graph = graph

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass

    def redo(self):
        self.execute()

    def _toggle(self, nodes: set[Node], edges: set[Edge], attr: str = "is_removed"):
        # Toggle nodes
        for node in nodes:
            toggle_node_attr(self.graph, node, attr)

        for src, dst, key in edges:
            # Toggle edges with key
            if key is not None:
                toggle_edge_attr(self.graph, src, dst, key, attr)
                continue

            # Toggle edges without key
            for u, v, key in find_edges(self.graph, src, dst):
                toggle_edge_attr(self.graph, u, v, key, attr)


CommandFunc = Callable[..., Optional[Command]]
