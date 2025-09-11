import time
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Callable, Optional, TypedDict

import networkx as nx
from numpy import isinf

from crunner.common import GRAPH_PATH, HTML_PATH, POLYGON_PATH
from crunner.editor.command import Command, CommandFunc, save_graph
from crunner.editor.command.add_edge import AddEdgeCommand
from crunner.editor.command.add_edges import AddEdgesCommand
from crunner.editor.command.add_node import AddNodeCommand
from crunner.editor.command.add_nodes import AddNodesCommand
from crunner.editor.command.change_graph import ChangeGraphCommand
from crunner.editor.command.extend_graph import ExtendGraphCommand
from crunner.editor.command.find_circuit import FindCircuitCommand
from crunner.editor.command.remove_toggled import RemoveToggledCommand
from crunner.editor.command.save_graph import SaveGraphCommand
from crunner.editor.command.set_distances import SetDistancesCommand
from crunner.editor.command.split_graph import split_graph_menu
from crunner.editor.command.toggle_highlighted import toggle_highlighted_menu
from crunner.editor.command.toggle_removed import toggle_menu
from crunner.editor.command.toggle_type import toggle_type_menu
from crunner.explore import Explorer
from crunner.graph import ToggleOption
from crunner.handler import Handler


class EditorOptions(TypedDict):
    auto_save: Optional[bool]
    auto_circuit: Optional[bool]
    toggle_opt: Optional[ToggleOption]


DEFAULT_OPTIONS: EditorOptions = {
    "auto_save": False,
    "auto_circuit": False,
    "toggle_opt": ToggleOption.KEEP_LARGEST,
}


class Editor:
    def __init__(self):
        # Graph
        self.explorer = Explorer()
        self.handler = Handler()
        self.graph: Optional[nx.MultiDiGraph] = None
        self.path: Optional[Path] = None

        # Commands
        self.COMMAND_MAP: dict[str, tuple[str, Callable]] = {}
        self.COMMAND_LIST: list[Callable] = []
        self.command_history: list[Command] = []
        self.command_redos: list[Command] = []

    def __create_edit_prompt(self):
        opts = "\n".join(
            f"[{idx:>2} | {shorthand:>3}] {label}"
            for idx, (shorthand, (label, _)) in enumerate(
                self.COMMAND_MAP.items(), start=1
            )
        )

        return f"""\
What would you like to do?
--------------------------
{opts}
--------------------------
[{self.path.stem}]
Enter here (or press Q to quit): """

    def do(self, command: int | str | Command):
        if not isinstance(command, Command):
            # Choose command based on chosen position in list
            if isinstance(command, int):
                if not (0 <= command < len(self.COMMAND_MAP)):
                    return

                command_func = self.COMMAND_LIST[command]

            # Choose command based on its identifier
            elif isinstance(command, str):
                if command not in self.COMMAND_MAP:
                    return

                # Create the command and execute if valid
                _, command_func = self.COMMAND_MAP[command]

            # Execute command if any was chosen
            command = command_func()

        if command is None:
            return

        command.execute()

        # Register command in history for undo/redoing
        self.command_history.append(command)

    def undo(self):
        if not self.command_history:
            print("Nothing to undo")
            return

        command = self.command_history.pop()
        command.undo()

        self.command_redos.append(command)

    def redo(self):
        if not self.command_redos:
            print("Nothing to redo")
            return

        command = self.command_redos.pop()
        command.redo()

        self.command_history.append(command)

    def save_graph(self, path):
        path = path if path else input("Name for the graph (without extension): ")
        self.handler.save(self.graph, path)

    def edit(
        self,
        graph: nx.MultiDiGraph,
        path: Path,
        opts: EditorOptions = {},
    ):
        opts = {**DEFAULT_OPTIONS, **opts}

        self.graph = graph
        self.path = path

        self.COMMAND_MAP = {
            "T": (
                "Toggle removed",
                partial(
                    toggle_menu,
                    graph=self.graph,
                    toggle_opt=opts["toggle_opt"],
                ),
            ),
            # "TE": (
            #     "Toggle removed (edge type)",
            #     partial(
            #         toggle_type_menu,
            #         graph=self.graph,
            #         toggle_opt=toggle_opt,
            #     ),
            # ),
            # "TH": (
            #     "Toggle highlighted",
            #     partial(toggle_highlighted_menu, graph=self.graph),
            # ),
            "AN": (
                "Add node",
                partial(AddNodeCommand, graph=self.graph),
            ),
            "ANS": (
                "Add nodes",
                partial(AddNodesCommand, graph=self.graph),
            ),
            "AE": (
                "Add edge",
                partial(AddEdgeCommand, graph=self.graph),
            ),
            "AES": ("Add edges", partial(AddEdgesCommand, graph=self.graph)),
            "R": (
                "Remove toggled",
                partial(
                    RemoveToggledCommand,
                    graph=self.graph,
                ),
            ),
            "X": (
                "Split graph",
                partial(split_graph_menu, graph=self.graph, path=path),
            ),
            "E": (
                "Extend with existing graph",
                partial(ExtendGraphCommand, graph=self.graph),
            ),
            "C": (
                "Find circuit for graph",
                partial(
                    FindCircuitCommand,
                    graph=self.graph,
                    path=path,
                    auto_circuit=opts["auto_circuit"],
                ),
            ),
            "D": (
                "Set distances based on geography",
                partial(SetDistancesCommand, graph=self.graph),
            ),
            "S": (
                "Save as",
                partial(SaveGraphCommand, graph=self.graph, path=path),
            ),
            "U": ("Undo", self.undo),
            "Y": ("Redo", self.redo),
        }
        self.COMMAND_LIST = [func for _, func in self.COMMAND_MAP.values()]

        output = ""
        prompt = self.__create_edit_prompt()

        while True:
            self.explorer.explore_roads(self.graph, path)
            if opts["auto_save"]:
                self.save_graph(path)

            # Ask the user for the next command
            output = input(prompt)
            if output.upper() == "Q":
                break

            # Perform the command
            if not output.isdigit():
                self.do(output)
            else:
                idx = int(output) - 1
                self.do(idx)

        return self.graph
