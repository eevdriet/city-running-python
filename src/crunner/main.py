from pathlib import Path

import networkx as nx

from crunner.editor import Editor
from crunner.graph import (
    ToggleOption,
    convert_to_simple_undirected,
    find_partitions_from_dist,
    total_length,
)
from crunner.handler import Handler
from crunner.plotter import Plotter
from crunner.route import Postman

# Load in graph to edit

# Edit the graph as much as you like
toggle_opt = ToggleOption.KEEP_FROM_NODE
editor = Editor()
graph, path = editor.ask_for_graph()
graph = editor.edit(graph, path, auto_save=True, toggle_opt=toggle_opt)

# Find a circuit for the current graph
postman = Postman()
source = int(input("Source for the circuit: "))
circuit, graph = postman.rpp_undirected(graph, source=source)

# # Plot the circuit
plotter = Plotter()
plotter.plot_circuit(graph, circuit)

# 109-108
# 106-64
# 314-23
pass
