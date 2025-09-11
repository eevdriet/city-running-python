import json
from pathlib import Path
from typing import Optional

from crunner.common import STREET_PATH
from crunner.graph import find_streets
from crunner.handler import Handler

handler = Handler()


def compare_streets(path: Optional[Path] = None, debug: bool = False):
    if path and len(path.parents) == 0:
        return

    if not path:
        _, path = handler.ask_for_graph()
        if not path:
            return

        path = path.relative_to(path.parent.parent)

    city = (
        path.parent
        if len(path.parents) == 1
        else path.parent.relative_to(path.parents[1])
    )

    with open(STREET_PATH / path.with_suffix(".json"), "r", encoding="utf-8") as file:
        streets_ox = set(json.load(file))

    STRIDES_PATH = STREET_PATH / city / "city_strides"
    with open(STRIDES_PATH / "all.json", "r", encoding="utf-8") as file:
        streets_strides = set(json.load(file))
    with open(STRIDES_PATH / "todo.json", "r", encoding="utf-8") as file:
        streets_todo = set(json.load(file))
    with open(STRIDES_PATH / "completed.json", "r", encoding="utf-8") as file:
        streets_completed = set(json.load(file))

    streets_both = streets_ox & streets_strides
    print(
        f"Streets in both {path.stem} ({len(streets_ox)}) and CityStrides ({len(streets_strides)}): {len(streets_both)}"
    )
    print(f"\t- Only in {path.stem}: {len(streets_ox - streets_strides)}")
    print(f"\t- Only in CityStrides: {len(streets_strides - streets_ox)}")

    frac_completed = len(streets_ox & streets_completed) / len(streets_both)
    print(
        f"Streets completed: {len(streets_ox & streets_completed)} ({100 * frac_completed:.3f}%)"
    )
    if debug:
        for street in sorted(list(streets_ox & streets_completed)):
            print(f"\t- {street}")

    frac_todo = len(streets_ox & streets_todo) / len(streets_both)
    print(f"Streets todo: {len(streets_ox & streets_todo)} ({100 * frac_todo:.3f}%)")
    if debug:
        for street in sorted(list(streets_ox & streets_todo)):
            print(f"\t- {street}")

    # print(list(sorted(list(streets_completed - streets_ox))))


def get_streets(debug: bool = False):
    graph, path = handler.ask_for_graph()
    if not graph or not path:
        return

    # Save graph when getting streets if it is the whole city
    if path.stem == path.parent.stem:
        if len(path.parts) >= 2:
            path = Path(*path.parts[-2:])
        handler.save(graph, path)

    streets = find_streets(graph)
    streets = list(streets)
    streets.sort()

    print(f"Found {len(streets)} streets for {path.name}!")
    if debug:
        for street in streets:
            print(f"\t- {street}")

    path = path.relative_to(path.parent.parent)

    with open(STREET_PATH / path.with_suffix(".json"), "w", encoding="utf-8") as file:
        json.dump(streets, file, indent=4)
        return


if __name__ == "__main__":
    PATH_BINNEN = Path("Rotterdam") / "_BINNEN.json"
    PATH_ALL = Path("Rotterdam") / "Rotterdam.json"
    compare_streets(PATH_ALL, debug=False)
