from itertools import islice
from pathlib import Path
from typing import Optional, override

import networkx as nx

from crunner.editor.command import Command, input_nodes_edges
from crunner.graph import Edge, Node, ToggleOption, find_components
from crunner.handler import Handler


class SplitGraphCommand(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        path: Path,
        nodes: set[Node],
        edges: set[Edge],
    ):
        super().__init__(graph)

        self.path = path
        self.nodes = nodes
        self.edges = edges

        self.handler = Handler()

    def __find_and_toggle(self):
        # -- Finding components -- #
        # 1. Toggle all nodes for removal to determine components
        # 2. Per component, determine which edges connect to the nodes that are removed

        # -- Saving components -- #
        # 1. Toggle back nodes to

        # Add edges that connect to the node to toggle
        for node in self.nodes:
            for edge in self.graph.in_edges(node, keys=True):
                self.edges.add(edge)
            for edge in self.graph.out_edges(node, keys=True):
                self.edges.add(edge)

        self.edges = {
            (src, dst, key[0] if len(tup) == 3 else None)
            for tup in self.edges
            for src, dst, *key in [tup]
        }

        self._toggle(self.nodes, self.edges)

    def __save_graphs(self):
        components = find_components(self.graph, ToggleOption.KEEP_ALL)
        self._toggle(self.nodes, self.edges)

        # List components (show 5 nodes or all if it has fewer)
        for n, component in enumerate(components, start=1):
            n_nodes = len(component)
            nodes = list(component) if n_nodes < 5 else list(islice(component, 5))
            print(f"Component {n} has {n_nodes} nodes: {nodes}")

        # Save components
        print("Saving (empty for no saving, otherwise give name)")
        for n, component in enumerate(components, start=1):
            # Ask for the name, blank skips saving
            name = input(f"Component {n}?: ")
            if not name:
                continue

            if False:
                # Ask which nodes to add back (e.g. when you want to keep a dividing road in both components)
                print("Which nodes do you want to add back to the component?")
                # nodes = {
                #     dst
                #     for dst in set(self.graph.nodes) - component
                #     if any(self.graph.has_edge(src, dst) for src in component)
                # }
                output = input(", ".join(str(node) for node in self.nodes) + ": ")
                if output:
                    chosen_nodes = (
                        self.nodes
                        if output == "all"
                        else [int(node) for node in output.replace(" ", "").split(",")]
                    )
                    component.update(chosen_nodes)
            else:
                component.update(self.nodes)

            # for node in component:
            #     data = self.graph.nodes[node]
            #     data["is_removed"] = False

            path = self.path.with_stem(name)
            graph = nx.subgraph(self.graph, component)
            self.handler.save(graph, path)

    @override
    def execute(self):
        # 1 Toggle nodes just like with toggle_elem
        self.__find_and_toggle()
        self.__save_graphs()

        # 2 Identify all subcomponents

        # 3 Ask to save which component to which file

    @override
    def undo(self):
        self._toggle(self.nodes, self.edges)

    @override
    def redo(self):
        self._toggle(self.nodes, self.edges)
        self.__save_graphs()


def split_graph_menu(graph: nx.Graph, path: Path) -> Optional[SplitGraphCommand]:
    nodes, edges = input_nodes_edges("to split into components")
    if not nodes and not edges:
        return None

    return SplitGraphCommand(graph, path, nodes, edges)
