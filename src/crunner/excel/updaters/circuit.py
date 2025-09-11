import json
from pathlib import Path
from typing import Iterator, override

import send2trash

from crunner.common import CIRCUIT_PATH
from crunner.excel.header import Header
from crunner.excel.updaters import ExcelUpdater


class CircuitDistanceUpdater(ExcelUpdater):
    def __init__(self, area: str, should_overwrite: bool = True):
        header = Header.DISTANCE
        super().__init__(
            "Circuit distance", area, header, should_overwrite=should_overwrite
        )

    @override
    def _find_new_values(self):
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)

            dist = data.get("total_distance_m")
            return [dist] if dist is None else [round(dist / 1000, 3)]
        except:
            print(f"Trashing {self.path} as it is invalid")
            send2trash.send2trash(self.path)
            return []

    @override
    def find_paths(self) -> Iterator[Path]:
        return (CIRCUIT_PATH / self.area).rglob("*.json")
