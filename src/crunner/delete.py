import re
import sys
from pathlib import Path
from typing import Optional

import send2trash

from crunner.common import DATA_PATH
from crunner.path import Paths
from crunner.util import find_path_name


def ends_with(path: Path, suffix: Path) -> bool:
    # Compare directories directly
    n_parts = len(suffix.parts)
    if path.parts[-n_parts:-1] != suffix.parts[:-1]:
        return False

    # Compare file without stem
    return (
        not suffix.suffixes and path.stem == suffix.stem
    ) or path.suffixes == suffix.suffixes


def delete():
    area = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Give the name of the area to delete: ")
    )
    if not area:
        return

    area = Path(area)

    for path in Paths.find(area):
        if Paths.data_type(path) in ["runs", "plotted"]:
            continue

        print(f"\t- Deleting {Paths.relative(path)}")
        send2trash.send2trash(path)


if __name__ == "__main__":
    delete()
