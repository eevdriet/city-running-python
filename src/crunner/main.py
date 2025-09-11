import sys

from crunner.editor import Editor, EditorOptions
from crunner.graph import ToggleOption
from crunner.handler import Handler


# Load in graph to edit
def main():
    handler = Handler()

    suffix = sys.argv[1] if len(sys.argv) > 1 else None
    result = handler.ask_for_graph2(suffix)
    if not result:
        return

    graph, path = result
    editor = Editor()

    opts: EditorOptions = {
        "auto_save": False,
        "auto_circuit": False,
        "toggle_opt": ToggleOption.KEEP_FROM_NODE,
    }
    graph = editor.edit(graph, path, opts)


if __name__ == "__main__":
    main()
