from pathlib import Path

from crunner.common import GRAPH_PATH, OFFSET_PATH, PLOTTED_PATH
from crunner.editor import Editor
from crunner.editor.command.find_circuit import FindCircuitCommand
from crunner.handler import Handler
from crunner.util import find_path_name

handler = Handler()
editor = Editor()

for path in (GRAPH_PATH / "Rotterdam").rglob("*.graphml"):
    name = find_path_name(path).with_suffix(".gpx")
    print(name)

    if (PLOTTED_PATH / name).exists() or (OFFSET_PATH / name).exists():
        print(f"Already plotted circuit for {path.stem}")
        continue

    graph = handler.load_from_file(path)
    if not graph or not path:
        continue

    print(f"Finding circuit for {path.stem}")
    editor.do(FindCircuitCommand(graph, name, True))
