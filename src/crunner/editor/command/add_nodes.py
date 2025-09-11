from typing import override

import networkx as nx
from geopy.distance import geodesic

from crunner.editor.command import Command
from crunner.graph import Node, find_node_location


class AddNodesCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

        self.ids: list[int] = []
        self.datas: dict[int, dict] = {}

    @override
    def execute(self):
        while True:
            try:
                lat = float(input("Latitude: "))
                lng = float(input("Longitude: "))
            except ValueError:
                break

            id = len(self.graph.nodes)
            self.datas[id] = {"y": lat, "x": lng}

            self.ids.append(id)
            self.graph.add_node(id, **self.datas[id])

    @override
    def undo(self):
        for id in self.ids:
            self.graph.remove_node(id)

    @override
    def redo(self):
        for id in self.ids:
            data = self.datas[id]
            id = len(self.graph) + 1
            self.graph.add_node(id, **data)
