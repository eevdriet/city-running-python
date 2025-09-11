from typing import override

import networkx as nx
from geopy.distance import geodesic

from crunner.editor.command import Command
from crunner.graph import Node, find_node_location


class AddNodeCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

        self.id: int = None
        self.data: dict = {}

    @override
    def execute(self):
        try:
            lat = float(input("Latitude: "))
            lng = float(input("Longitude: "))
        except ValueError:
            print("Could not read lat/lng, skipping...")
            return

        self.data = {"y": lat, "x": lng}
        self.id = len(self.graph.nodes)

        self.graph.add_node(self.id, **self.data)

    @override
    def undo(self):
        self.graph.remove_node(self.id)

    @override
    def redo(self):
        self.id = len(self.graph) + 1
        self.graph.add_node(self.id, **self.data)
