from itertools import islice
from pathlib import Path
from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import Edge, Node, ToggleOption, find_components
from crunner.handler import Handler


class ShowByNameCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        name: str,
    ):
        super().__init__(graph)

        self.name = name
        self.edges: set[Edge] = set()

    def __has_name(self, data: dict, name: str):
        if "name" not in data:
            return False

        names = data["name"]
        if isinstance(names, list):
            return name in names

        return names == name

    @override
    def execute(self):
        self.edges = {
            edge
            for *edge, data in self.graph.edges(keys=True, data=True)
            if self.__has_name(data, self.name)
        }

        nodes, edges = set(), self.edges
        self._toggle(nodes, edges, "is_highlighted")

    @override
    def undo(self):
        nodes, edges = set(), self.edges
        self._toggle(nodes, edges, "is_highlighted")

    @override
    def redo(self):
        nodes, edges = set(), self.edges
        self._toggle(nodes, edges, "is_highlighted")


def show_by_name_menu(graph: nx.Graph) -> Optional[ShowByNameCommand]:
    name = input("List name of roads to toggle: ")
    if not name:
        return None

    return ShowByNameCommand(graph, name)
