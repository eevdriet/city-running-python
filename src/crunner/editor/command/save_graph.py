from pathlib import Path
from typing import override

import networkx as nx

from crunner.editor.command import Command
from crunner.handler import Handler


class SaveGraphCommand(Command):
    def __init__(self, graph: nx.MultiDiGraph, path: Path | None = None):
        super().__init__(graph)
        self.path = path

        self.handler = Handler()

    @override
    def execute(self):
        if not self.path:
            path = input("Give a path to save the current graph to: ")
            if not path:
                return

            self.path = Path(path)

        self.handler.save(self.graph, self.path)

    @override
    def undo(self):
        pass

    @override
    def redo(self):
        pass
