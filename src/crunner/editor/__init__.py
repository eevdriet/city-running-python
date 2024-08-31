from functools import partial
from pathlib import Path

import networkx as nx
from flask import Flask, render_template

from crunner.common import GRAPH_PATH, HTML_PATH, POLYGON_PATH
from crunner.editor.command import Command, CommandFunc
from crunner.editor.command.remove_toggled import RemoveToggledCommand
from crunner.editor.command.show_by_name import show_by_name_menu
from crunner.editor.command.split_graph import split_graph_menu
from crunner.editor.command.toggle_elem import toggle_elem_menu
from crunner.editor.command.toggle_type import toggle_type_menu
from crunner.explore import Explorer
from crunner.graph import ToggleOption
from crunner.handler import Handler


class Editor:
    def __init__(self):
        # Graph
        self.explorer = Explorer()
        self.handler = Handler()
        self.graph: nx.MultiDiGraph = None

        # App
        self.app = Flask(__name__, template_folder=HTML_PATH)
        self.app.add_url_rule("/", view_func=self.render)

        # Commands
        self.COMMAND_MAP: list[tuple[str, callable]] = []
        self.command_history: list[Command] = []
        self.command_redos: list[Command] = []

    def render(self):
        return render_template("map.html")

    def __create_graph_prompt(self):
        prompt = """\
How would you like to load the graph?
--------------------------
"""
        for idx, (label, _, _) in enumerate(self.LOAD_MAP, start=1):
            prompt += f"[{idx}] {label}\n"
        prompt += f"""\
--------------------------
Enter here: """

        return prompt

    def __create_edit_prompt(self):
        prompt = """\
What would you like to do?
--------------------------
"""
        for idx, (label, _) in enumerate(self.COMMAND_MAP, start=1):
            prompt += f"[{idx}] {label}\n"

        prompt += f"""\
[{len(self.COMMAND_MAP) + 1}] Undo
[{len(self.COMMAND_MAP) + 2}] Redo
--------------------------
Enter here: """

        return prompt

    def do(self, command_idx: int):
        # Create the command and execute if valid
        _, command_func = self.COMMAND_MAP[command_idx]

        command = command_func()
        if command is None:
            return

        self.command_history.append(command)
        command.execute()

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

    def ask_for_graph(self):
        self.LOAD_MAP: list[tuple[str, callable, Path]] = [
            ("Load from graph file", self.handler.load_from_file, GRAPH_PATH),
            (
                "Load from polygon file",
                self.handler.load_from_polygon_file,
                POLYGON_PATH,
            ),
        ]

        prompt = self.__create_graph_prompt()

        while True:
            output = input(prompt)
            if not output or not output.isdigit():
                break

            idx = int(output) - 1
            if not (0 <= idx < len(self.LOAD_MAP)):
                continue

            _, load_func, base_path = self.LOAD_MAP[idx]

            path = Path(input("Give a path to load from: "))
            full_path = base_path / path
            if not full_path.exists():
                continue

            return load_func(full_path), full_path

    def edit(
        self,
        graph: nx.MultiDiGraph,
        path: Path,
        auto_save: bool = False,
        toggle_opt: ToggleOption = ToggleOption.KEEP_LARGEST,
    ):
        self.app.run(debug=True)
        self.graph = graph
        self.COMMAND_MAP: list[tuple[str, CommandFunc]] = [
            (
                "Toggle nodes/edges",
                partial(
                    toggle_elem_menu,
                    graph=self.graph,
                    toggle_opt=toggle_opt,
                ),
            ),
            (
                "Toggle edge type",
                partial(
                    toggle_type_menu,
                    graph=self.graph,
                    toggle_opt=toggle_opt,
                ),
            ),
            (
                "Remove toggled",
                partial(
                    RemoveToggledCommand,
                    graph=self.graph,
                ),
            ),
            (
                "Split graph",
                partial(split_graph_menu, graph=self.graph, path=path),
            ),
            (
                "Show by name",
                partial(show_by_name_menu, graph=self.graph),
            ),
        ]

        output = ""
        prompt = self.__create_edit_prompt()

        while True:
            # Plot the current state of the graph
            self.explorer.explore_roads(self.graph)

            # Ask the user for the next command
            output = input(prompt)
            if not output or not output.isdigit():
                break

            idx = int(output) - 1

            if 0 <= idx < len(self.COMMAND_MAP):
                self.do(idx)
            elif idx == len(self.COMMAND_MAP):
                self.undo()
            elif idx == len(self.COMMAND_MAP) + 1:
                self.redo()
            else:
                continue

            if auto_save:
                self.save_graph(path)

        return self.graph


if __name__ == "__main__":
    editor = Editor()
    path = Path("Rotterdam") / "Nieuwe Werk"
    # graph = editor.handler.load_from_polygon_file(path)
    graph = editor.handler.load_from_file(path)

    editor.edit(
        graph,
        path,
        auto_save=True,
        toggle_opt=ToggleOption.KEEP_LARGEST,
    )
