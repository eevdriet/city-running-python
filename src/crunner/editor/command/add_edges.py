from typing import override

import networkx as nx
from geopy.distance import geodesic
from shapely import LineString
from veelog import setup_logger

from crunner.editor.command import Command
from crunner.graph import Edge, Node, find_node_location

logger = setup_logger(__name__)


class AddEdgesCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

        self.edges: set[Edge] = set()
        self.data: dict = {}

    @override
    def execute(self):
        prev = 0
        ask_for_nodes = True
        ask_for_first = True

        while ask_for_nodes:
            try:
                if ask_for_first:
                    node = input("First node:")
                    prev = int(node)
                    ask_for_first = False

                match node := input(f"Next node ({prev}): "):
                    case "n" | "N":
                        ask_for_first = True
                        continue
                    case _:
                        curr = int(node)
                        edge: Edge = (prev, curr)
                        edge_rev: Edge = (curr, prev)

                        if not edge_rev in self.edges:
                            self.edges.add(edge)

                        prev = curr

            except ValueError:
                ask_for_nodes = False

        self.is_undirected = True  # input("Is undirected (Y/N)?: ").lower() == "y"
        self.data["highway"] = "footway"
        self.data["oneway"] = not self.is_undirected
        self.data["self_created"] = True

        for src, dst, *_ in self.edges:
            # Calculate the distance as a straight line
            coord_src = find_node_location(self.graph, src)
            coord_dst = find_node_location(self.graph, dst)

            # logger.info(f"{src} ({coord_src}) -> {dst} ({coord_dst})")
            if coord_src and coord_dst:
                self.data["distance"] = geodesic(coord_src, coord_dst).meters
                self.data["geometry"] = LineString([coord_src, coord_dst])
                # logger.info(f"\tDistance: {self.data["distance"]}")

            # Add edge
            self.graph.add_edge(src, dst, **self.data)
            if self.is_undirected:
                self.graph.add_edge(dst, src, **self.data)

    @override
    def undo(self):
        for src, dst, *_ in self.edges:
            self.graph.remove_edge(src, dst)

            if self.is_undirected:
                self.graph.remove_edge(dst, src)

    @override
    def redo(self):
        for src, dst, *_ in self.edges:
            self.graph.add_edge(src, dst, **self.data)

            if self.is_undirected:
                self.graph.add_edge(dst, src, **self.data)
