from typing import override

import networkx as nx
from geopy.distance import geodesic
from shapely import LineString
from veelog import setup_logger

from crunner.editor.command import Command
from crunner.graph import Node, find_node_location

logger = setup_logger(__name__)


class AddEdgeCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

        self.src: Node = None
        self.dst: Node = None
        self.is_undirected = False
        self.data: dict = {}

    @override
    def execute(self):
        try:
            self.src = int(input("Source node: "))
            self.dst = int(input("Destination node: "))
        except ValueError:
            return

        self.is_undirected = True  # input("Is undirected (Y/N)?: ").lower() == "y"
        self.data["highway"] = "footway"
        self.data["oneway"] = not self.is_undirected
        self.data["self_created"] = True

        # Calculate the distance as a straight line
        coord_src = find_node_location(self.graph, self.src)
        coord_dst = find_node_location(self.graph, self.dst)

        # logger.info(f"{self.src} ({coord_src}) -> {self.dst} ({coord_dst})")
        if coord_src and coord_dst:
            self.data["distance"] = geodesic(coord_src, coord_dst).meters
            self.data["geometry"] = LineString([coord_src[::-1], coord_dst[::-1]])
            # logger.info(f"\tDistance: {self.data["distance"]}")

        # Add edge
        self.graph.add_edge(self.src, self.dst, **self.data)
        # if self.is_undirected:
        #     self.graph.add_edge(self.dst, self.src, **self.data)

    @override
    def undo(self):
        self.graph.remove_edge(self.src, self.dst)

        if self.is_undirected:
            self.graph.remove_edge(self.dst, self.src)

    @override
    def redo(self):
        self.graph.add_edge(self.src, self.dst, **self.data)

        if self.is_undirected:
            self.graph.add_edge(self.dst, self.src, **self.data)
