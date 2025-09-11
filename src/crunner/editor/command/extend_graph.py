from typing import override

import networkx as nx

from crunner.editor.command import Command
from crunner.graph import (
    Edge,
    Node,
    contains_edge,
    contains_node,
    find_edge,
    find_edges,
    find_node,
    toggle_edge_attr,
    toggle_node_attr,
)
from crunner.handler import Handler


class ExtendGraphCommand(Command):
    REMOVE_EXTENDED = False

    def __init__(self, graph: nx.MultiDiGraph):
        super().__init__(graph)

        self.handler = Handler()
        self.node_map: dict[Node, Node] = {}
        self.added_nodes: dict[Node, dict] = {}
        self.added_edges: dict[Edge, dict] = {}

    @override
    def execute(self):
        # Ask for graph to extend from
        other_graph, _ = self.handler.ask_for_graph()
        if other_graph is None:
            return

        # Add all nodes that do not have the exact same data as an existing node
        node_id = len(self.graph.nodes) + 2

        print("Adding nodes...")
        for node, data in other_graph.nodes(data=True):
            # Node is already in the graph
            if (other_node := find_node(data, self.graph)) is not None:
                self.node_map[node] = other_node
                continue

            # Add the node (as removed) to the current graph
            self.node_map[node] = node_id
            data["is_removed"] = self.REMOVE_EXTENDED

            self.graph.add_node(node_id, **data)
            self.added_nodes[node_id] = data

            node_id += 1

        print("Adding edges...")
        for src, dst, key, data in other_graph.edges(keys=True, data=True):
            # Edge is already in the graph
            if contains_edge(src, dst, key, other_graph, self.graph):
                continue

            # Find the nodes that the edge belongs to from the original or new graph
            data["is_removed"] = self.REMOVE_EXTENDED
            u = self.node_map[src]
            v = self.node_map[dst]

            # Find the keys of all edges already between the nodes
            keys = set(self.graph[u][v].keys()) if self.graph.has_edge(u, v) else set()

            # Add the edge and refine the keys to only be the newly added
            self.graph.add_edge(u, v, **data)
            new_keys = set(self.graph[u][v].keys()) - keys

            # Should only be one key added
            if len(new_keys) != 1:
                print("ERROR: Somehow multiple new keys")
                continue

            # Save the edge data with the key which it was added with
            key = new_keys.pop()

            data["is_removed"] = True
            self.added_edges[(u, v, key)] = data

    @override
    def undo(self):
        self.graph.remove_nodes_from(self.added_nodes.keys())
        self.graph.remove_edges_from(self.added_edges.keys())

    @override
    def redo(self):
        for node, data in self.added_nodes.items():
            self.graph.add_node(node, **data)

        for *edge, data in self.added_edges.items():
            self.graph.add_node(*edge, **data)
