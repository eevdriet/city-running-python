from typing import override

import networkx as nx
from geopy.distance import geodesic
from veelog import setup_logger

from crunner.editor.command import Command
from crunner.graph import Node, find_node_location

logger = setup_logger(__name__)


class SetDistancesCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

    @override
    def execute(self):
        for src, dst, key, data in self.graph.edges(data=True, keys=True):
            # Do not overwrite correctly set distances
            if data.get("distance", 0):
                continue

            # Calculate the distance as a straight line
            coord_src = find_node_location(self.graph, src)
            coord_dst = find_node_location(self.graph, dst)

            logger.info(f"{src} ({coord_src}) -> {dst} ({coord_dst})")

            if coord_src and coord_dst:
                data["distance"] = geodesic(coord_src, coord_dst).meters
                logger.info(f"\tDistance: {data["distance"]}")

    @override
    def undo(self):
        pass

    @override
    def redo(self):
        pass
