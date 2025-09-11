import shutil
from pathlib import Path

from crunner.path import Paths


def rename():
    try:
        area = Path(input("Give the name of the area to rename: "))
    except:
        return

    new_area = Path(input("Give the name to rename area into: "))

    print("Renaming")
    for path in Paths.find(area):
        new_path = Paths.resolve(path, new_area, path.suffix)

        print(f"\t- {Paths.relative(path)} -> {Paths.relative(new_path)}")
        shutil.move(path, new_path)


if __name__ == "__main__":
    rename()
