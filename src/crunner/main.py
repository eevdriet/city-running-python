import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox

from crunner.explore import Explorer
from crunner.handler import Handler
from crunner.plotter import Plotter
from crunner.route import Postman

name = "Middelland-Noord"
graph = Handler.load_from_file(name)

explorer = Explorer()
explorer.explore_roads(graph)

postman = Postman()
SOURCE = 27
circuit = postman.rpp_undirected(graph, source=SOURCE)

plotter = Plotter()
plotter.plot_circuit(graph, circuit)
