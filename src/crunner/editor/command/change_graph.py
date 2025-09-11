from typing import override

from crunner.editor.command import Command
from crunner.handler import Handler


class ChangeGraphCommand(Command):
    def __init__(self, editor: any):
        self.editor = editor
        super().__init__(editor.graph)

        self.handler = Handler()

    @override
    def execute(self):
        graph, path = self.handler.ask_for_graph()
        if not graph or not path:
            return

        self.editor.graph = graph
        self.editor.path = path

    @override
    def undo(self):
        pass

    @override
    def redo(self):
        pass
