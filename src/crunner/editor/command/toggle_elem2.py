from functools import partial
from typing import Optional, override

import ipyleaflet as ipl
import networkx as nx
from IPython.display import display

from crunner.editor.command import Command
from crunner.graph import (
    Edge,
    Node,
    ToggleOption,
    find_disconnected_elements,
    find_edges,
    toggle_edge_attr,
    toggle_node_attr,
)
from crunner.plotter2 import LeafletPlotter


class ToggleElemCommand2(Command):
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        mapp: ipl.Map,
        toggle_opt: ToggleOption,
    ):
        super().__init__(graph)

        self.map = mapp
        self.toggle_opt = toggle_opt

    def __find_and_toggle(self):
        for marker in self.map.layers:
            marker.on_click(partial(self.on_marker_clicked, marker))

    @override
    def execute(self): ...

    @override
    def undo(self):
        self._toggle(self.nodes, self.edges)

    @override
    def redo(self):
        self._toggle(self.nodes, self.edges)
