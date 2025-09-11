import json
from pathlib import Path

import send2trash

from crunner.common import CIRCUIT_PATH, DATA_PATH, GPX_PATH, GRAPH_PATH, RUNS_PATH
from crunner.gpx import to_gpx
from crunner.handler import Handler
from crunner.plotter import Plotter
from crunner.route import Postman


def generate_circuits():
    handler = Handler()
    postman = Postman()
    plotter = Plotter()

    for circuit_path in (CIRCUIT_PATH / "Rotterdam").iterdir():
        if circuit_path.suffix != ".json":
            continue

        graph_path = GRAPH_PATH / "Rotterdam" / f"{circuit_path.stem}.graphml"
        if not graph_path.exists():
            continue

        with open(circuit_path, "r") as file:
            circuit_data = json.load(file)

        if not "source" in circuit_data:
            continue
        if "circuit" in circuit_data:
            continue

        source = circuit_data["source"]
        graph = handler.load_from_file(graph_path)
        circuit, graph, stats = postman.rpp_undirected(graph, source)

        path = Path("Rotterdam") / graph_path.name
        plotter.plot_circuit(graph, circuit, path, stats)


def generate_gpx():
    handler = Handler()

    print("Generating GPX files...")
    for graph_path in (GRAPH_PATH / "Rotterdam").iterdir():
        circuit_path = CIRCUIT_PATH / "Rotterdam" / f"{graph_path.stem}.json"
        if not circuit_path.exists():
            continue

        print(f"\t- {graph_path.stem}")

        try:
            with open(circuit_path, "r") as file:
                stats = json.load(file)
        except:
            print("\t\t Deleting because corrupted")
            send2trash.send2trash(circuit_path)
            continue

        if not "circuit" in stats:
            print(f"\t\t No circuit: {circuit_path.name}")
            continue

        graph = handler.load_from_file(graph_path)
        circuit = stats["circuit"]

        gpx_path = GPX_PATH / "Rotterdam" / f"{graph_path.stem}.gpx"
        print(f"\t\t{gpx_path.resolve()}")
        to_gpx(circuit, graph, gpx_path, stats)


if __name__ == "__main__":
    generate_gpx()
