import shutil
from pathlib import Path

from crunner.common import DATA_PATH
from crunner.util import ends_with, find_path_name


def create_region():
    try:
        area = Path(input("Give the name of the region to create: "))
    except:
        return

    for path in DATA_PATH.iterdir():
        if path.is_dir() and not "excel" in path.parts:
            new_path = path / area
            print(f"\t- Creating {new_path.resolve()} ({path})")
            new_path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    create_region()
